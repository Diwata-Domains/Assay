"""CLI entrypoint tests."""

import re
from pathlib import Path

from typer.testing import CliRunner

from assay import __version__
from assay.cli.main import app

runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})


def _plain(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"assay {__version__}" in result.output


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--verbose" in _plain(result.output)


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


def test_report_no_packets(tmp_path: Path) -> None:
    cfg = tmp_path / "assay.toml"
    cfg.write_text(f'[store]\ndb = "{tmp_path}/empty.db"\n')
    result = runner.invoke(app, ["--config", str(cfg), "report"])
    assert result.exit_code == 0
    assert "no packets found" in result.output



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
