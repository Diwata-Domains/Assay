"""Assay CLI entrypoint."""

from __future__ import annotations

import getpass
import secrets
import shutil
from pathlib import Path
from typing import Optional, cast

import typer

from assay import __version__
from assay.config import AssayConfig, ConfigError, load_config
from assay.formatter.formatter import format_packet
from assay.formatter.writer import write_packet
from assay.keys.store import KeyStoreError, create_key, list_keys, revoke_key
from assay.runner import artifacts as _artifacts
from assay.runner import runner as _runner
from assay.schedule.cron import InvalidCronError, validate_cron
from assay.schedule.store import ScheduleStoreError, add_schedule, list_schedules, remove_schedule

app = typer.Typer(
    help="Assay — independent verification layer for software projects.",
    invoke_without_command=True,
)
schedule_app = typer.Typer(help="Manage scheduled test runs.")
key_app = typer.Typer(help="Manage API keys for the ingest endpoint.")
store_app = typer.Typer(help="Manage the SQLite packet store.")
admin_app = typer.Typer(help="Admin credential management.")

app.add_typer(schedule_app, name="schedule")
app.add_typer(key_app, name="key")
app.add_typer(store_app, name="store")
app.add_typer(admin_app, name="admin")

_NOT_IMPLEMENTED = "not implemented"

_TOML_TEMPLATE = """\
[project]
name = "{name}"

[output]
directory = "{output_dir}"

[serve]
host = "0.0.0.0"
port = {port}

[keys]
store = "~/.assay/keys.json"

[store]
db = "~/.assay/store.db"

[schedule]
store = "~/.assay/schedules.json"
"""


@app.command()
def init(
    force: bool = typer.Option(False, "--force", help="Overwrite existing assay.toml without prompting."),
) -> None:
    """Interactive first-run setup: write assay.toml and print .env block."""
    config_path = Path("assay.toml")

    if config_path.exists() and not force:
        overwrite = typer.confirm(f"{config_path} already exists. Overwrite?", default=False)
        if not overwrite:
            typer.echo("Aborted.")
            raise typer.Exit(0)

    typer.echo("Setting up Assay. Press Enter to accept defaults.\n")

    name = typer.prompt("Project name", default=Path.cwd().name)
    output_dir = typer.prompt("Output directory", default="./assay-output")
    port = typer.prompt("Serve port", default=8000)
    admin_email = typer.prompt("Admin email")

    password = getpass.getpass("Admin password: ")
    if not password:
        typer.echo("error: password cannot be empty", err=True)
        raise typer.Exit(1)
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        typer.echo("error: passwords do not match", err=True)
        raise typer.Exit(1)

    from assay.auth.admin import hash_password
    password_hash = hash_password(password)
    jwt_secret = secrets.token_urlsafe(32)

    config_path.write_text(
        _TOML_TEMPLATE.format(name=name, output_dir=output_dir, port=port),
        encoding="utf-8",
    )

    typer.echo("\nassay.toml written.\n")
    typer.echo("Add these to your .env (do not commit this file):\n")
    typer.echo(f"ASSAY_ADMIN_EMAIL={admin_email}")
    typer.echo(f"ASSAY_ADMIN_PASSWORD_HASH={password_hash}")
    typer.echo(f"ASSAY_JWT_SECRET={jwt_secret}")
    typer.echo("\nRun:  assay serve")


@app.callback()
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(  # noqa: UP007
        None,
        "--version",
        help="Print version and exit.",
    ),
    config: Optional[str] = typer.Option(  # noqa: UP007
        None,
        "--config",
        help="Override config file path.",
        envvar="ASSAY_CONFIG",
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose output."),
) -> None:
    try:
        ctx.obj = load_config(config)
    except ConfigError as exc:
        typer.echo(f"config error: {exc}", err=True)
        raise typer.Exit(2) from exc
    if version:
        typer.echo(f"assay {__version__}")
        raise typer.Exit(0)


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


@app.command()
def run(
    ctx: typer.Context,
    target: Optional[str] = typer.Option(None, "--target", help="URL or target to test."),  # noqa: UP007
    script: Optional[str] = typer.Option(None, "--script", help="Path to an Assay script JSON file (multi-step run)."),  # noqa: UP007
    suite: str = typer.Option("default", "--suite", help="Test suite name."),
    output: Optional[str] = typer.Option(None, "--output", help="Output directory."),  # noqa: UP007
    task_id: Optional[str] = typer.Option(None, "--task-id", help="Grain task ID to tag this run."),  # noqa: UP007
    verification_id: Optional[str] = typer.Option(None, "--verification-id", help="Grain-issued VERIFY-XXXX-NNN ID."),  # noqa: UP007
    submit: bool = typer.Option(False, "--submit", help="Submit packet to Grain output path after run."),
    watch: bool = typer.Option(False, "--watch", help="Re-run on file changes (Ctrl+C to exit)."),
    watch_path: str = typer.Option(".", "--watch-path", help="Directory to watch for changes (default: current dir)."),
    compare: bool = typer.Option(
        False, "--compare", help="Diff screenshot against stored baseline; exit 1 on regression."
    ),
    threshold: float = typer.Option(0.1, "--threshold", help="Regression threshold as % changed pixels (default 0.1)."),
    no_docker: bool = typer.Option(False, "--no-docker", help="Run Playwright directly via Node.js (requires node + playwright installed)."),  # noqa: E501
) -> None:
    """Execute a test run using the Playwright + Docker runner.

    Single-URL mode:   assay run --target https://example.com
    Multi-step mode:   assay run --script login-flow.json
    """
    from assay.grain.detect import detect_task_id

    if script is not None:
        _run_script_mode(
            ctx=ctx,
            script_path=script,
            suite=suite,
            output=output,
            task_id=task_id,
            verification_id=verification_id,
            submit=submit,
            no_docker=no_docker,
        )
        return

    if target is None:
        typer.echo("error: --target or --script is required", err=True)
        raise typer.Exit(2)

    config: AssayConfig = ctx.obj
    output_dir = output or config.output.directory
    image = config.runner.docker_image

    # Resolve task_id: explicit flag > Grain auto-detect
    effective_task_id = task_id or detect_task_id(config.grain.project_root or None)
    if effective_task_id:
        typer.echo(f"task_id: {effective_task_id}")

    def _do_run() -> str:
        if no_docker:
            runner_result = _runner.run_direct(target, suite=suite, output_dir=output_dir)
        else:
            runner_result = _runner.run(target, suite=suite, output_dir=output_dir, image=image)
        try:
            bundle = _artifacts.collect_artifacts(runner_result.output_dir, runner_result)
        except _artifacts.ArtifactError as exc:
            typer.echo(f"error reading artifacts: {exc}", err=True)
            raise typer.Exit(1) from exc
        typer.echo(f"outcome: {bundle.outcome}")
        if bundle.error:
            typer.echo(f"error: {bundle.error}", err=True)
        try:
            packet = format_packet(bundle, task_id=effective_task_id, verification_id=verification_id)
            packet["url"] = bundle.url or str(target)
            vid = str(packet["verification_id"])
            candidate_png: Optional[Path] = None
            if bundle.screenshot_path:
                src = Path(bundle.screenshot_path)
                if src.exists():
                    dest = Path(output_dir) / f"{vid}.png"
                    shutil.copy2(src, dest)
                    packet["artifact_refs"] = [str(dest)]
                    candidate_png = dest
            packet_path = write_packet(packet, output_dir)
            typer.echo(f"packet: {packet_path}")
            _store_packet(packet, config)
        except Exception as exc:
            typer.echo(f"error writing packet: {exc}", err=True)
            raise typer.Exit(1) from exc
        if submit:
            _do_submit(str(packet_path), config)
        if compare and candidate_png is not None:
            _do_compare(str(target), candidate_png, vid, output_dir, config, threshold)
        return bundle.outcome

    if not watch:
        outcome = _do_run()
        if outcome == "pass":
            raise typer.Exit(0)
        elif outcome == "fail":
            raise typer.Exit(3)
        else:
            raise typer.Exit(1)

    from assay.watch.poller import debounce_and_wait, parse_watch_target, watch_once

    wp, watch_glob = parse_watch_target(watch_path)
    label = str(wp.resolve()) + (f"/{watch_glob}" if watch_glob else "")
    typer.echo(f"watching: {label} (Ctrl+C to stop)")
    try:
        _do_run()
        while True:
            watch_once(wp, glob=watch_glob)
            debounce_and_wait(wp, debounce_ms=500, glob=watch_glob)
            typer.echo("--- change detected, re-running ---")
            _do_run()
    except KeyboardInterrupt:
        typer.echo("\nwatch stopped")
        raise typer.Exit(0)


def _run_script_mode(
    ctx: typer.Context,
    script_path: str,
    suite: str,
    output: Optional[str],  # noqa: UP007
    task_id: Optional[str],  # noqa: UP007
    verification_id: Optional[str],  # noqa: UP007
    submit: bool,
    no_docker: bool = False,
) -> None:
    """Execute a multi-step Assay script and write a structured result packet."""
    from assay.scripts.parser import ScriptParseError, parse_script

    script_file = Path(script_path)
    if not script_file.exists():
        typer.echo(f"error: script file not found: {script_path}", err=True)
        raise typer.Exit(2)

    try:
        assay_script = parse_script(script_file)
    except ScriptParseError as exc:
        typer.echo(f"error: invalid script: {exc}", err=True)
        raise typer.Exit(2) from exc

    typer.echo(f"script: {assay_script.name} ({len(assay_script.steps)} steps)")

    config: AssayConfig = ctx.obj
    output_dir = output or config.output.directory
    image = config.runner.docker_image

    from assay.grain.detect import detect_task_id
    from assay.runner import runner as _runner_mod
    from assay.runner.artifacts import collect_artifacts

    effective_task_id = task_id or detect_task_id(config.grain.project_root or None)

    import tempfile
    run_output_dir = output_dir or tempfile.mkdtemp(prefix="assay-script-")
    Path(run_output_dir).mkdir(parents=True, exist_ok=True)

    if no_docker:
        runner_result = _runner_mod.run_script_direct(script_file, suite=suite, output_dir=run_output_dir)
    else:
        import subprocess
        docker_cmd = _find_docker_binary()
        if docker_cmd is None:
            typer.echo("error: docker not found — use --no-docker to run without Docker", err=True)
            raise typer.Exit(1)
        cmd = [
            docker_cmd, "run", "--rm",
            "-e", f"ASSAY_SCRIPT_FILE=/scripts/{script_file.name}",
            "-e", f"ASSAY_SUITE={suite}",
            "-e", "ASSAY_OUTPUT_DIR=/output",
            "-v", f"{run_output_dir}:/output",
            "-v", f"{script_file.parent.resolve()}:/scripts:ro",
            image,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        from assay.runner.runner import RunResult
        runner_result = RunResult(
            exit_code=result.returncode,
            output_dir=run_output_dir,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    try:
        bundle = collect_artifacts(run_output_dir, runner_result)
    except Exception as exc:
        typer.echo(f"error reading script artifacts: {exc}", err=True)
        raise typer.Exit(1) from exc

    # Print step summary
    for step in bundle.steps:
        icon = "✓" if step.outcome == "pass" else "✗"
        shot = f" [{step.screenshot_path}]" if step.screenshot_path else ""
        err_detail = f" — {step.error}" if step.error else ""
        typer.echo(f"  {icon} step {step.index}: {step.label}{err_detail}{shot}")

    typer.echo(f"outcome: {bundle.outcome}")

    packet = format_packet(bundle, task_id=effective_task_id, verification_id=verification_id)
    packet_path = write_packet(packet, run_output_dir)
    typer.echo(f"packet: {packet_path}")
    _store_packet(packet, config)

    if submit:
        _do_submit(str(packet_path), config)

    raise typer.Exit(0 if bundle.outcome == "pass" else 1)


def _find_docker_binary() -> Optional[str]:  # noqa: UP007
    """Return docker binary path or None."""
    try:
        from assay.runner.runner import _find_docker
        return _find_docker()
    except FileNotFoundError:
        return None


def _do_compare(
    url: str,
    candidate_png: Path,
    verification_id: str,
    output_dir: str,
    config: AssayConfig,
    threshold: float,
) -> None:
    from assay.diff.engine import DiffError
    from assay.diff.engine import diff_images as _diff
    from assay.store.db import get_baseline_for_url as _get_bl
    from assay.store.db import init_db

    db_path = Path(config.store.db).expanduser()
    init_db(db_path)
    baseline = _get_bl(url, db_path)
    if baseline is None:
        typer.echo(f"compare: no baseline set for {url}")
        return

    bl_refs = baseline.get("artifact_refs", [])
    baseline_png: Optional[Path] = None
    for ref in (bl_refs if isinstance(bl_refs, list) else []):
        bp = Path(str(ref))
        if bp.suffix == ".png" and "_diff" not in bp.stem and bp.exists():
            baseline_png = bp
            break

    if baseline_png is None:
        typer.echo("compare: baseline has no screenshot on disk — skipping diff")
        return

    diff_path = Path(output_dir) / f"{verification_id}_diff.png"
    try:
        result = _diff(baseline_png, candidate_png, diff_path)
    except DiffError as exc:
        typer.echo(f"compare: diff failed: {exc}", err=True)
        return

    typer.echo(
        f"diff: {result.diff_pct}% changed ({result.changed_pixels}/{result.total_pixels} pixels)"
    )
    if result.diff_pct > threshold:
        typer.echo(f"REGRESSION detected (>{threshold}%)", err=True)
        raise typer.Exit(1)
    else:
        typer.echo(f"clean — within threshold ({threshold}%)")


def _store_packet(packet: dict[str, object], config: AssayConfig) -> None:
    from assay.store.db import init_db
    from assay.store.db import insert_packet as _insert

    db_path = Path(config.store.db).expanduser()
    try:
        init_db(db_path)
        _insert(packet, db_path)
    except Exception:
        pass


def _do_submit(packet_path: str, config: AssayConfig) -> None:
    """Copy a packet to the configured Grain output path."""
    import json as _json

    grain_output = config.grain.output_path
    if not grain_output:
        typer.echo("error: [grain] output_path not configured", err=True)
        raise typer.Exit(1)

    try:
        data = _json.loads(Path(packet_path).read_text())
    except Exception as exc:
        typer.echo(f"error reading packet: {exc}", err=True)
        raise typer.Exit(1) from exc

    import re as _re

    import jsonschema  # type: ignore[import-untyped]

    from assay.schemas import ASSAY_PAYLOAD
    try:
        jsonschema.validate(instance=data, schema=ASSAY_PAYLOAD)
    except jsonschema.ValidationError as exc:
        typer.echo(f"error: packet schema invalid: {exc.message}", err=True)
        raise typer.Exit(1) from exc

    vid = str(data.get("verification_id", ""))
    _UUID_RE = _re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", _re.I)
    if _UUID_RE.match(vid):
        typer.echo(
            "warning: verification_id is a UUID — grain verify ingest will reject this packet; "
            "use --verification-id VERIFY-XXXX-NNN to set the grain-issued ID",
            err=True,
        )

    dest_dir = Path(grain_output)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(packet_path).name
    shutil.copy2(packet_path, dest)
    typer.echo(f"submitted: {dest}")


# ---------------------------------------------------------------------------
# submit
# ---------------------------------------------------------------------------


@app.command()
def submit(
    ctx: typer.Context,
    packet: str = typer.Option(..., "--packet", help="Path to the packet JSON file to submit."),
) -> None:
    """Validate and submit a packet to the configured Grain output path."""
    config: AssayConfig = ctx.obj
    _do_submit(packet, config)


# ---------------------------------------------------------------------------
# serve
# ---------------------------------------------------------------------------


@app.command()
def serve(
    ctx: typer.Context,
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind."),
    port: int = typer.Option(8000, "--port", help="Port to bind."),
) -> None:
    """Start the FastAPI ingest server."""
    import uvicorn

    from assay.ingest.app import app as ingest_app

    config: AssayConfig = ctx.obj
    ingest_app.state.key_store = config.keys.store
    ingest_app.state.output_dir = config.output.directory
    ingest_app.state.store_db = config.store.db

    uvicorn.run(ingest_app, host=host, port=port)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


@app.command()
def report(
    ctx: typer.Context,
    output: str = typer.Option("./assay-output", "--output", help="Output directory (used for html screenshot paths)."),
    format: str = typer.Option("text", "--format", help="Output format: text, json, or html."),
    filter: Optional[str] = typer.Option(None, "--filter", help="Filter packets, e.g. outcome=fail."),  # noqa: UP007
    open: bool = typer.Option(False, "--open", help="Open the report in the default browser (html only)."),
    export: Optional[str] = typer.Option(  # noqa: UP007
        None, "--export", help="Write matching packets as JSON array to this file path."
    ),
    checks: bool = typer.Option(False, "--checks", help="Include check results alongside packets."),
) -> None:
    """Display task packet summaries from the SQLite store."""
    import json as _json
    from pathlib import Path as _Path

    from assay.store.db import list_packets

    config: AssayConfig = ctx.obj
    db_path = _Path(config.store.db).expanduser()
    packets: list[dict[str, object]] = list_packets(db_path)

    check_results: list[dict[str, object]] = []
    if checks:
        from assay.store.db import list_check_results
        check_results = list_check_results(db_path)

    # Apply --filter key=value
    if filter:
        if "=" not in filter:
            typer.echo("error: --filter must be in key=value form", err=True)
            raise typer.Exit(2)
        fkey, fval = filter.split("=", 1)
        packets = [p for p in packets if str(p.get(fkey, "")) == fval]

    if export:
        _Path(export).write_text(_json.dumps(packets, indent=2), encoding="utf-8")
        typer.echo(f"exported: {export}")

    if open and format != "html":
        typer.echo("warning: --open is only supported with --format html")

    if format == "json":
        if checks:
            typer.echo(_json.dumps({"packets": packets, "checks": check_results}, indent=2))
        else:
            typer.echo(_json.dumps(packets, indent=2))
        raise typer.Exit(0)

    if format == "html":
        import webbrowser

        from assay.formatter.html_formatter import render_html

        html = render_html(packets)
        dest = _Path("assay-report.html")
        dest.write_text(html, encoding="utf-8")
        resolved = str(dest.resolve())
        typer.echo(f"report: {resolved}")
        if open:
            webbrowser.open(f"file://{resolved}")
        raise typer.Exit(0)

    if not packets and not check_results:
        typer.echo("no check results found" if checks else "no packets found")
        raise typer.Exit(0)

    # Text table — packets
    if packets:
        col = "{:<36}  {:<13}  {:<8}  {:<10}  {:<10}  {}"
        typer.echo(col.format("verification_id", "outcome", "severity", "screenshot", "verified_at", "summary"))
        typer.echo("-" * 120)
        for p in packets:
            vid = str(p.get("verification_id", ""))[:36]
            outcome = str(p.get("outcome", ""))
            severity = str(p.get("severity", ""))
            refs = cast(list[object], p.get("artifact_refs", []))
            has_screenshot = "yes" if any(str(r).endswith(".png") for r in refs) else "no"
            verified_at = str(p.get("verified_at", ""))[:10]
            summary = str(p.get("summary", ""))
            typer.echo(col.format(vid, outcome, severity, has_screenshot, verified_at, summary))

    if checks and check_results:
        typer.echo("\n-- check results --")
        ccol = "{:<24}  {:<10}  {:<44}  {}"
        typer.echo(ccol.format("check_id", "type", "target", "status"))
        typer.echo("-" * 96)
        for r in check_results:
            status = "PASS" if r.get("passed") else "FAIL"
            typer.echo(ccol.format(
                str(r.get("check_id", ""))[:24],
                str(r.get("check_type", ""))[:10],
                str(r.get("target", ""))[:44],
                status,
            ))
    elif checks:
        typer.echo("\nno check results found")


# ---------------------------------------------------------------------------
# schedule subcommands
# ---------------------------------------------------------------------------


@schedule_app.command("add")
def schedule_add(
    ctx: typer.Context,
    cron: str = typer.Option(..., "--cron", help="Cron expression (5-field)."),
    suite: str = typer.Option("default", "--suite", help="Test suite name."),
    target: Optional[str] = typer.Option(None, "--target", help="URL override (uses config default if omitted)."),  # noqa: UP007
) -> None:
    """Register a new scheduled run."""
    try:
        validate_cron(cron)
    except InvalidCronError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc

    config: AssayConfig = ctx.obj
    try:
        sid = add_schedule(config.schedule.store, cron, suite=suite, target=target)
    except ScheduleStoreError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"schedule added: {sid}")


@schedule_app.command("list")
def schedule_list(ctx: typer.Context) -> None:
    """List all active schedules."""
    config: AssayConfig = ctx.obj
    try:
        schedules = list_schedules(config.schedule.store)
    except ScheduleStoreError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    if not schedules:
        typer.echo("no schedules")
        return
    for s in schedules:
        target = s["target"] or "(config default)"
        last = s["last_run"] or "never"
        typer.echo(f"{s['id']}  {s['cron']}  suite={s['suite']}  target={target}  last_run={last}")


@schedule_app.command("run")
def schedule_run(ctx: typer.Context) -> None:
    """Start the scheduler loop (foreground; Ctrl+C to stop)."""
    from assay.schedule.loop import run_scheduler

    config: AssayConfig = ctx.obj
    run_scheduler(config)


@schedule_app.command("remove")
def schedule_remove(
    ctx: typer.Context,
    schedule_id: str = typer.Argument(..., help="Schedule ID to remove."),
) -> None:
    """Remove a schedule by ID."""
    config: AssayConfig = ctx.obj
    try:
        remove_schedule(config.schedule.store, schedule_id)
    except ScheduleStoreError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"removed: {schedule_id}")


@schedule_app.command("start")
def schedule_start(ctx: typer.Context) -> None:
    """Start the scheduler as a background daemon."""
    from assay.schedule.daemon import start

    start(config_path=None)


@schedule_app.command("stop")
def schedule_stop() -> None:
    """Stop the running background scheduler daemon."""
    from assay.schedule.daemon import stop

    stop()


@schedule_app.command("status")
def schedule_status() -> None:
    """Show whether the background scheduler daemon is running."""
    from assay.schedule.daemon import status

    info = status()
    if info["running"]:
        typer.echo(f"running (pid {info['pid']})")
    else:
        typer.echo("stopped")
    typer.echo(f"log: {info['log_file']}")


# ---------------------------------------------------------------------------
# key subcommands
# ---------------------------------------------------------------------------


@key_app.command("create")
def key_create(
    ctx: typer.Context,
    name: Optional[str] = typer.Option(None, "--name", help="Label for the key."),  # noqa: UP007
) -> None:
    """Generate a new API key."""
    config: AssayConfig = ctx.obj
    try:
        raw = create_key(config.keys.store, label=name)
    except KeyStoreError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"\nkey: {raw}")
    typer.echo("Save this key — it will not be shown again.\n")
    typer.echo("Test it:")
    typer.echo(f'  curl -sf <your-assay-endpoint>/health -H "X-Assay-Key: {raw}"\n')
    typer.echo("SDK (TypeScript):")
    typer.echo( "  import { AssaySDK } from '@diwata-labs/assay-sdk'")
    typer.echo(f"  const assay = AssaySDK.fromEnv()  // set ASSAY_API_KEY={raw} ASSAY_ENDPOINT=<url>")
    typer.echo( "  await assay.capture({ comment: 'first capture' })")


@key_app.command("list")
def key_list(ctx: typer.Context) -> None:
    """List all API keys (IDs and labels only)."""
    config: AssayConfig = ctx.obj
    try:
        keys = list_keys(config.keys.store)
    except KeyStoreError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    if not keys:
        typer.echo("no keys")
        return
    for k in keys:
        status = "revoked" if k["revoked"] else "active"
        typer.echo(f"{k['id']}  {k['label']}  {status}  {k['created_at']}")


@key_app.command("revoke")
def key_revoke(
    ctx: typer.Context,
    key_id: str = typer.Argument(..., help="Key ID to revoke."),
) -> None:
    """Revoke an API key by ID."""
    config: AssayConfig = ctx.obj
    try:
        revoke_key(config.keys.store, key_id)
    except KeyStoreError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"revoked: {key_id}")


# ---------------------------------------------------------------------------
# store subcommands
# ---------------------------------------------------------------------------


@store_app.command("import")
def store_import(
    ctx: typer.Context,
    dir: str = typer.Option(..., "--dir", help="Directory containing assay-*.json files to import."),
) -> None:
    """Import assay-*.json files from a directory into the SQLite store."""
    import json as _json
    from pathlib import Path as _Path

    from assay.store.db import import_packets, init_db

    config: AssayConfig = ctx.obj
    db_path = _Path(config.store.db).expanduser()
    init_db(db_path)

    src = _Path(dir)
    if not src.is_dir():
        typer.echo(f"error: directory not found: {dir}", err=True)
        raise typer.Exit(1)

    packets: list[dict[str, object]] = []
    for path in sorted(src.glob("assay-*.json")):
        try:
            data: dict[str, object] = _json.loads(path.read_text())
            packets.append(data)
        except Exception as exc:
            typer.echo(f"warning: skipping {path.name}: {exc}", err=True)

    count = import_packets(packets, db_path)
    typer.echo(f"imported: {count} packet(s)")


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


@app.command("check")
def check_cmd(
    ctx: typer.Context,
    check_id: Optional[str] = typer.Option(None, "--check", help="Run a single check by ID."),  # noqa: UP007
) -> None:
    """Run named checks defined in [[checks]] in assay.toml."""
    from assay.checks.models import CheckResult
    from assay.checks.runner import UnknownCheckType, run_check
    from assay.store.db import init_db, insert_check_result

    config: AssayConfig = ctx.obj
    checks = config.checks

    if check_id is not None:
        checks = [c for c in checks if c.id == check_id]
        if not checks:
            typer.echo(f"error: no check with id {check_id!r}", err=True)
            raise typer.Exit(2)

    if not checks:
        typer.echo("no checks configured — add [[checks]] blocks to assay.toml")
        raise typer.Exit(0)

    db_path = __import__("pathlib").Path(config.store.db).expanduser()
    init_db(db_path)

    results: list[CheckResult] = []
    for c in checks:
        try:
            result = run_check(c)
        except UnknownCheckType as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(2) from exc
        results.append(result)
        insert_check_result(
            {
                "check_id": result.check_id,
                "check_type": result.check_type,
                "target": result.target,
                "passed": result.passed,
                "assertions": [
                    {"name": a.name, "passed": a.passed, "expected": a.expected, "actual": a.actual}
                    for a in result.assertions
                ],
                "error": result.error,
                "checked_at": result.checked_at,
            },
            db_path,
        )

    col = "{:<24}  {:<10}  {:<44}  {}"
    typer.echo(col.format("id", "type", "target", "status"))
    typer.echo("-" * 96)
    any_failed = False
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        if not r.passed:
            any_failed = True
        typer.echo(col.format(r.check_id[:24], r.check_type[:10], r.target[:44], status))
        if r.error:
            typer.echo(f"  error: {r.error}", err=True)
        for a in r.assertions:
            icon = "✓" if a.passed else "✗"
            typer.echo(f"  {icon} {a.name}: expected={a.expected!r} actual={a.actual!r}")

    raise typer.Exit(1 if any_failed else 0)


# admin


@admin_app.command("set-password")
def admin_set_password() -> None:
    """Hash a password for use as ASSAY_ADMIN_PASSWORD_HASH."""
    import getpass

    from assay.auth.admin import hash_password

    password = getpass.getpass("Password: ")
    if not password:
        typer.echo("error: password cannot be empty", err=True)
        raise typer.Exit(1)
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        typer.echo("error: passwords do not match", err=True)
        raise typer.Exit(1)
    hashed = hash_password(password)
    typer.echo(f"\nAdd this to your .env:\n\nASSAY_ADMIN_PASSWORD_HASH={hashed}")
