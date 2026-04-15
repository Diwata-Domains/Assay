"""Assay CLI entrypoint."""

from __future__ import annotations

from typing import Optional

import typer

from assay import __version__
from assay.config import AssayConfig, ConfigError, load_config
from assay.runner import artifacts as _artifacts
from assay.runner import runner as _runner

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
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind."),
    port: int = typer.Option(8000, "--port", help="Port to bind."),
) -> None:
    """Start the FastAPI ingest server."""
    typer.echo(_NOT_IMPLEMENTED)
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


@app.command()
def report(
    output: str = typer.Option("./assay-output", "--output", help="Directory to read packets from."),
    format: str = typer.Option("text", "--format", help="Output format: text or json."),
) -> None:
    """Display or export task packet summaries."""
    typer.echo(_NOT_IMPLEMENTED)
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# schedule subcommands
# ---------------------------------------------------------------------------


@schedule_app.command("add")
def schedule_add(
    cron: str = typer.Option(..., "--cron", help="Cron expression (5-field)."),
    suite: str = typer.Option("default", "--suite", help="Test suite name."),
) -> None:
    """Register a new scheduled run."""
    typer.echo(_NOT_IMPLEMENTED)
    raise typer.Exit(1)


@schedule_app.command("list")
def schedule_list() -> None:
    """List all active schedules."""
    typer.echo(_NOT_IMPLEMENTED)
    raise typer.Exit(1)


@schedule_app.command("remove")
def schedule_remove(
    id: str = typer.Argument(..., help="Schedule ID to remove."),
) -> None:
    """Remove a schedule by ID."""
    typer.echo(_NOT_IMPLEMENTED)
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# key subcommands
# ---------------------------------------------------------------------------


@key_app.command("create")
def key_create(
    name: Optional[str] = typer.Option(None, "--name", help="Label for the key."),  # noqa: UP007
) -> None:
    """Generate a new API key."""
    typer.echo(_NOT_IMPLEMENTED)
    raise typer.Exit(1)


@key_app.command("list")
def key_list() -> None:
    """List all API keys (IDs and labels only)."""
    typer.echo(_NOT_IMPLEMENTED)
    raise typer.Exit(1)


@key_app.command("revoke")
def key_revoke(
    key_id: str = typer.Argument(..., help="Key ID to revoke."),
) -> None:
    """Revoke an API key by ID."""
    typer.echo(_NOT_IMPLEMENTED)
    raise typer.Exit(1)
