"""Config precedence tests — validates load_config() priority order.

Priority: explicit path > ./assay.toml > ~/.assay/config.toml > all-defaults.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from assay.config import AssayConfig, ConfigError, load_config


def _write_toml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# ---------------------------------------------------------------------------
# All-defaults (no config file found)
# ---------------------------------------------------------------------------


def test_defaults_returned_when_no_config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = load_config()
    assert isinstance(cfg, AssayConfig)
    assert cfg.project.name == "assay"
    assert cfg.runner.docker_image == "assay-playwright:latest"
    assert cfg.output.directory == "./assay-output"
    assert cfg.serve.host == "127.0.0.1"
    assert cfg.serve.port == 8000
    assert cfg.keys.store == "~/.assay/keys.json"
    assert cfg.schedule.store == "~/.assay/schedules.json"


# ---------------------------------------------------------------------------
# Explicit path overrides everything
# ---------------------------------------------------------------------------


def test_explicit_path_is_loaded(tmp_path: Path) -> None:
    config_file = tmp_path / "custom.toml"
    _write_toml(config_file, '[project]\nname = "my-project"\n')
    cfg = load_config(str(config_file))
    assert cfg.project.name == "my-project"


def test_explicit_path_not_found_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(str(tmp_path / "nonexistent.toml"))


# ---------------------------------------------------------------------------
# Project-local assay.toml
# ---------------------------------------------------------------------------


def test_project_local_toml_loaded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write_toml(tmp_path / "assay.toml", '[runner]\ndocker_image = "custom-image:v2"\n')
    cfg = load_config()
    assert cfg.runner.docker_image == "custom-image:v2"


def test_project_local_overrides_global(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_toml(tmp_path / "assay.toml", '[project]\nname = "local"\n')
    _write_toml(tmp_path / ".assay" / "config.toml", '[project]\nname = "global"\n')
    cfg = load_config()
    assert cfg.project.name == "local"


# ---------------------------------------------------------------------------
# Global ~/.assay/config.toml
# ---------------------------------------------------------------------------


def test_global_config_loaded_when_no_local(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_toml(tmp_path / ".assay" / "config.toml", '[output]\ndirectory = "/data/assay-out"\n')
    cfg = load_config()
    assert cfg.output.directory == "/data/assay-out"


# ---------------------------------------------------------------------------
# Section validation
# ---------------------------------------------------------------------------


def test_unknown_section_raises_config_error(tmp_path: Path) -> None:
    config_file = tmp_path / "bad.toml"
    _write_toml(config_file, '[unknown_section]\nkey = "value"\n')
    with pytest.raises(ConfigError, match="unknown config section"):
        load_config(str(config_file))


def test_invalid_toml_raises_config_error(tmp_path: Path) -> None:
    config_file = tmp_path / "bad.toml"
    config_file.write_text("{not valid toml")
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config(str(config_file))


def test_non_integer_timeout_raises_config_error(tmp_path: Path) -> None:
    config_file = tmp_path / "bad.toml"
    _write_toml(config_file, '[runner]\ntimeout_seconds = "three hundred"\n')
    with pytest.raises(ConfigError, match="timeout_seconds must be an integer"):
        load_config(str(config_file))


def test_schedule_store_configurable(tmp_path: Path) -> None:
    config_file = tmp_path / "assay.toml"
    _write_toml(config_file, '[schedule]\nstore = "/custom/schedules.json"\n')
    cfg = load_config(str(config_file))
    assert cfg.schedule.store == "/custom/schedules.json"
