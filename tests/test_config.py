"""Config loader tests."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from assay.cli.main import app
from assay.config import AssayConfig, ConfigError, load_config

runner = CliRunner(env={"NO_COLOR": "1"})


def test_defaults_when_no_file() -> None:
    cfg = load_config(None)
    assert isinstance(cfg, AssayConfig)
    assert cfg.serve.port == 8000
    assert cfg.serve.host == "127.0.0.1"
    assert cfg.runner.timeout_seconds == 300


def test_valid_full_config(tmp_path: Path) -> None:
    f = tmp_path / "assay.toml"
    f.write_text("[project]\nname = 'myapp'\n\n[serve]\nport = 9000\n")
    cfg = load_config(str(f))
    assert cfg.project.name == "myapp"
    assert cfg.serve.port == 9000
    assert cfg.serve.host == "127.0.0.1"  # default


def test_missing_explicit_file_raises() -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config("/nonexistent/assay.toml")


def test_invalid_toml_raises(tmp_path: Path) -> None:
    f = tmp_path / "assay.toml"
    f.write_text("this is not [ valid toml ===")
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config(str(f))


def test_unknown_section_raises(tmp_path: Path) -> None:
    f = tmp_path / "assay.toml"
    f.write_text("[unknown_section]\nfoo = 'bar'\n")
    with pytest.raises(ConfigError, match="unknown config section"):
        load_config(str(f))


def test_cli_config_missing_file_exits_2() -> None:
    result = runner.invoke(app, ["--config", "/nonexistent/assay.toml", "--version"])
    assert result.exit_code == 2


def test_cli_config_valid_file(tmp_path: Path) -> None:
    f = tmp_path / "assay.toml"
    f.write_text("[project]\nname = 'test'\n")
    result = runner.invoke(app, ["--config", str(f), "--version"])
    assert result.exit_code == 0
