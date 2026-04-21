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


def test_serve_starts_uvicorn() -> None:
    from unittest.mock import patch

    with patch("uvicorn.run") as mock_run:
        result = runner.invoke(app, ["serve"])
    assert result.exit_code == 0
    assert mock_run.called


def test_report_stub() -> None:
    result = runner.invoke(app, ["report"])
    assert result.exit_code == 1
    assert "not implemented" in result.output



def test_key_create_succeeds() -> None:
    result = runner.invoke(app, ["key", "create"])
    assert result.exit_code == 0
    assert "key:" in result.output


def test_key_list_empty() -> None:
    result = runner.invoke(app, ["key", "list"])
    assert result.exit_code == 0


def test_key_revoke_unknown_exits_1() -> None:
    result = runner.invoke(app, ["key", "revoke", "nonexistent-id"])
    assert result.exit_code == 1
