"""Assay CLI entrypoint."""

from __future__ import annotations

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

app.add_typer(schedule_app, name="schedule")
app.add_typer(key_app, name="key")

_NOT_IMPLEMENTED = "not implemented"


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
    suite: str = typer.Option("default", "--suite", help="Test suite name."),
    output: Optional[str] = typer.Option(None, "--output", help="Output directory."),  # noqa: UP007
) -> None:
    """Execute a test run using the Playwright + Docker runner."""
    if target is None:
        typer.echo("error: --target is required", err=True)
        raise typer.Exit(2)

    config: AssayConfig = ctx.obj
    output_dir = output or config.output.directory
    image = config.runner.docker_image

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
        packet = format_packet(bundle)
        # Copy screenshot to a stable verification_id-based name in the output dir
        verification_id = str(packet["verification_id"])
        if bundle.screenshot_path:
            src = Path(bundle.screenshot_path)
            if src.exists():
                dest = Path(output_dir) / f"{verification_id}.png"
                shutil.copy2(src, dest)
                packet["artifact_refs"] = [str(dest)]
        packet_path = write_packet(packet, output_dir)
        typer.echo(f"packet: {packet_path}")
    except Exception as exc:
        typer.echo(f"error writing packet: {exc}", err=True)
        raise typer.Exit(1) from exc

    if bundle.outcome == "pass":
        raise typer.Exit(0)
    elif bundle.outcome == "fail":
        raise typer.Exit(3)
    else:
        raise typer.Exit(1)


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

    uvicorn.run(ingest_app, host=host, port=port)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


@app.command()
def report(
    output: str = typer.Option("./assay-output", "--output", help="Directory to read packets from."),
    format: str = typer.Option("text", "--format", help="Output format: text or json."),
    filter: Optional[str] = typer.Option(None, "--filter", help="Filter packets, e.g. outcome=fail."),  # noqa: UP007
) -> None:
    """Display task packet summaries from the output directory."""
    import json as _json
    from pathlib import Path as _Path

    out = _Path(output)
    if not out.is_dir():
        typer.echo(f"error: output directory not found: {output}", err=True)
        raise typer.Exit(1)

    packets = []
    for path in sorted(out.glob("assay-*.json")):
        try:
            data: dict[str, object] = _json.loads(path.read_text())
        except Exception:
            continue
        packets.append(data)

    # Apply --filter key=value
    if filter:
        if "=" not in filter:
            typer.echo("error: --filter must be in key=value form", err=True)
            raise typer.Exit(2)
        fkey, fval = filter.split("=", 1)
        packets = [p for p in packets if str(p.get(fkey, "")) == fval]

    if format == "json":
        typer.echo(_json.dumps(packets, indent=2))
        raise typer.Exit(0)

    if not packets:
        typer.echo("no packets found")
        raise typer.Exit(0)

    # Text table
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
    typer.echo(f"key: {raw}")
    typer.echo("Save this key — it will not be shown again.")


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
