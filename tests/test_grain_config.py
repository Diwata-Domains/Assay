"""Tests for extended [grain] config fields (Phase 26 T01)."""

from __future__ import annotations

from pathlib import Path

from assay.config import load_config


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


# ---------------------------------------------------------------------------
# parsing phase/branch fields
# ---------------------------------------------------------------------------


def test_grain_phase_and_branch_fields(tmp_path: Path) -> None:
    cfg = _write(
        tmp_path,
        """
[grain]
phase = "P26"
branch = "main"
""",
    )
    c = load_config(str(cfg))
    assert c.grain.phase == "P26"
    assert c.grain.branch == "main"


def test_grain_partial_fields(tmp_path: Path) -> None:
    cfg = _write(
        tmp_path,
        "[grain]\nphase = 'P26'\n",
    )
    c = load_config(str(cfg))
    assert c.grain.phase == "P26"
    assert c.grain.branch == ""
