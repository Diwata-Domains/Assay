"""Tests for the [ci] config section."""

from __future__ import annotations

from pathlib import Path

import pytest

from assay.config import AssayConfig, CiConfig, ConfigError, load_config


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "assay.toml"
    p.write_text(content, encoding="utf-8")
    return p


def test_ci_defaults_when_section_absent(tmp_path):
    p = _write(tmp_path, "[project]\nname = 'test'\n")
    cfg = load_config(str(p))
    assert cfg.ci.compare is False
    assert cfg.ci.threshold == 0.1
    assert cfg.ci.fail_on_regression is True
    assert cfg.ci.comment is True


def test_ci_reads_all_fields(tmp_path):
    p = _write(tmp_path, """
[project]
name = "test"

[ci]
compare = true
threshold = 0.5
fail_on_regression = false
comment = false
""")
    cfg = load_config(str(p))
    assert cfg.ci.compare is True
    assert cfg.ci.threshold == 0.5
    assert cfg.ci.fail_on_regression is False
    assert cfg.ci.comment is False


def test_ci_partial_overrides(tmp_path):
    p = _write(tmp_path, "[ci]\ncompare = true\n")
    cfg = load_config(str(p))
    assert cfg.ci.compare is True
    assert cfg.ci.threshold == 0.1  # default preserved


def test_unknown_section_still_raises(tmp_path):
    p = _write(tmp_path, "[notavalidsection]\nkey = 'val'\n")
    with pytest.raises(ConfigError, match="unknown config section"):
        load_config(str(p))


def test_ci_config_dataclass_defaults():
    ci = CiConfig()
    assert ci.compare is False
    assert ci.threshold == 0.1
    assert ci.fail_on_regression is True
    assert ci.comment is True


def test_assay_config_has_ci():
    cfg = AssayConfig()
    assert hasattr(cfg, "ci")
    assert isinstance(cfg.ci, CiConfig)
