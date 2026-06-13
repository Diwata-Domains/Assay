"""Tests for extended [grain] config fields (Phase 26 T01)."""

from __future__ import annotations

from pathlib import Path

import pytest

from assay.config import ConfigError, load_config


def _write(tmp_path: Path, body: str) -> Path:
    cfg = tmp_path / "assay.toml"
    cfg.write_text(body, encoding="utf-8")
    return cfg


# ---------------------------------------------------------------------------
# defaults
# ---------------------------------------------------------------------------


def test_grain_defaults_when_section_absent(tmp_path: Path) -> None:
    cfg = _write(tmp_path, "[project]\nname = 'x'\n")
    c = load_config(str(cfg))
    assert c.grain.repo == ""
    assert c.grain.auto_create is False
    assert c.grain.phase == ""
    assert c.grain.branch == ""


def test_grain_existing_fields_unaffected(tmp_path: Path) -> None:
    cfg = _write(
        tmp_path,
        "[grain]\nproject_root = '/x'\noutput_path = '/y'\n",
    )
    c = load_config(str(cfg))
    assert c.grain.project_root == "/x"
    assert c.grain.output_path == "/y"
    assert c.grain.auto_create is False


# ---------------------------------------------------------------------------
# parsing all four new fields
# ---------------------------------------------------------------------------


def test_grain_all_new_fields(tmp_path: Path) -> None:
    cfg = _write(
        tmp_path,
        """
[grain]
repo = "/home/user/diwata-labs"
auto_create = true
phase = "P26"
branch = "main"
""",
    )
    c = load_config(str(cfg))
    assert c.grain.repo == "/home/user/diwata-labs"
    assert c.grain.auto_create is True
    assert c.grain.phase == "P26"
    assert c.grain.branch == "main"


def test_grain_auto_create_false(tmp_path: Path) -> None:
    cfg = _write(tmp_path, "[grain]\nauto_create = false\n")
    c = load_config(str(cfg))
    assert c.grain.auto_create is False


def test_grain_auto_create_string_true(tmp_path: Path) -> None:
    cfg = _write(tmp_path, '[grain]\nauto_create = "true"\n')
    c = load_config(str(cfg))
    assert c.grain.auto_create is True


def test_grain_auto_create_string_false(tmp_path: Path) -> None:
    cfg = _write(tmp_path, '[grain]\nauto_create = "false"\n')
    c = load_config(str(cfg))
    assert c.grain.auto_create is False


def test_grain_auto_create_invalid_raises(tmp_path: Path) -> None:
    cfg = _write(tmp_path, "[grain]\nauto_create = 42\n")
    with pytest.raises(ConfigError, match="auto_create must be a boolean"):
        load_config(str(cfg))


def test_grain_auto_create_invalid_string_raises(tmp_path: Path) -> None:
    cfg = _write(tmp_path, '[grain]\nauto_create = "yes"\n')
    with pytest.raises(ConfigError, match="auto_create must be a boolean"):
        load_config(str(cfg))


def test_grain_partial_fields(tmp_path: Path) -> None:
    cfg = _write(
        tmp_path,
        "[grain]\nrepo = '/repo'\nauto_create = true\n",
    )
    c = load_config(str(cfg))
    assert c.grain.repo == "/repo"
    assert c.grain.auto_create is True
    assert c.grain.phase == ""
    assert c.grain.branch == ""
