"""CLI entrypoint tests."""

from typer.testing import CliRunner

from assay import __version__
from assay.cli.main import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"assay {__version__}" in result.output


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--verbose" in result.output


def test_verbose_flag() -> None:
    result = runner.invoke(app, ["--verbose", "--version"])
    assert result.exit_code == 0


def test_run_requires_target() -> None:
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 2


def test_serve_stub() -> None:
    result = runner.invoke(app, ["serve"])
    assert result.exit_code == 1
    assert "not implemented" in result.output


def test_report_stub() -> None:
    result = runner.invoke(app, ["report"])
    assert result.exit_code == 1
    assert "not implemented" in result.output


def test_schedule_add_stub() -> None:
    result = runner.invoke(app, ["schedule", "add", "--cron", "0 2 * * *"])
    assert result.exit_code == 1
    assert "not implemented" in result.output


def test_schedule_list_stub() -> None:
    result = runner.invoke(app, ["schedule", "list"])
    assert result.exit_code == 1
    assert "not implemented" in result.output


def test_schedule_remove_stub() -> None:
    result = runner.invoke(app, ["schedule", "remove", "sched-001"])
    assert result.exit_code == 1
    assert "not implemented" in result.output


def test_key_create_stub() -> None:
    result = runner.invoke(app, ["key", "create"])
    assert result.exit_code == 1
    assert "not implemented" in result.output


def test_key_list_stub() -> None:
    result = runner.invoke(app, ["key", "list"])
    assert result.exit_code == 1
    assert "not implemented" in result.output


def test_key_revoke_stub() -> None:
    result = runner.invoke(app, ["key", "revoke", "key-001"])
    assert result.exit_code == 1
    assert "not implemented" in result.output
