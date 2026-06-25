"""Tests for the [review] config section (Phase 30, P30-T02)."""

from __future__ import annotations

from pathlib import Path

import pytest

from assay.config import AssayConfig, ConfigError, ReviewConfig, load_config


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "assay.toml"
    p.write_text(content, encoding="utf-8")
    return p


def test_review_defaults_when_section_absent(tmp_path: Path) -> None:
    p = _write(tmp_path, "[project]\nname = 'test'\n")
    cfg = load_config(str(p))
    assert cfg.review.mode == "adversarial"
    assert cfg.review.repo == "."
    assert cfg.review.base == ""
    assert cfg.review.head == ""
    assert cfg.review.model == ""
    assert cfg.review.agent_count == 2
    assert cfg.review.needs_fix_threshold == 1


def test_review_reads_all_fields(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
[review]
mode = "proposer-critic"
repo = "/srv/app"
base = "main"
head = "feature/x"
model = "claude-opus-4-8"
agent_count = 3
needs_fix_threshold = 2
""",
    )
    cfg = load_config(str(p))
    assert cfg.review.mode == "proposer-critic"
    assert cfg.review.repo == "/srv/app"
    assert cfg.review.base == "main"
    assert cfg.review.head == "feature/x"
    assert cfg.review.model == "claude-opus-4-8"
    assert cfg.review.agent_count == 3
    assert cfg.review.needs_fix_threshold == 2


def test_review_partial_overrides(tmp_path: Path) -> None:
    p = _write(tmp_path, "[review]\nbase = 'main'\nhead = 'HEAD'\n")
    cfg = load_config(str(p))
    assert cfg.review.base == "main"
    assert cfg.review.head == "HEAD"
    assert cfg.review.agent_count == 2  # default preserved
    assert cfg.review.mode == "adversarial"  # default preserved


def test_review_agent_count_must_be_int(tmp_path: Path) -> None:
    p = _write(tmp_path, "[review]\nagent_count = 'two'\n")
    with pytest.raises(ConfigError, match="agent_count must be an integer"):
        load_config(str(p))


def test_review_needs_fix_threshold_must_be_int(tmp_path: Path) -> None:
    p = _write(tmp_path, "[review]\nneeds_fix_threshold = 1.5\n")
    with pytest.raises(ConfigError, match="needs_fix_threshold must be an integer"):
        load_config(str(p))


def test_review_agent_count_rejects_bool(tmp_path: Path) -> None:
    p = _write(tmp_path, "[review]\nagent_count = true\n")
    with pytest.raises(ConfigError, match="agent_count must be an integer"):
        load_config(str(p))


def test_review_agent_count_must_be_positive(tmp_path: Path) -> None:
    p = _write(tmp_path, "[review]\nagent_count = 0\n")
    with pytest.raises(ConfigError, match="agent_count must be >= 1"):
        load_config(str(p))


def test_review_needs_fix_threshold_must_be_positive(tmp_path: Path) -> None:
    p = _write(tmp_path, "[review]\nneeds_fix_threshold = 0\n")
    with pytest.raises(ConfigError, match="needs_fix_threshold must be >= 1"):
        load_config(str(p))


def test_review_section_must_be_table(tmp_path: Path) -> None:
    p = _write(tmp_path, "review = 'oops'\n")
    with pytest.raises(ConfigError, match=r"\[review\] must be a table"):
        load_config(str(p))


def test_review_config_dataclass_defaults() -> None:
    rc = ReviewConfig()
    assert rc.mode == "adversarial"
    assert rc.repo == "."
    assert rc.agent_count == 2
    assert rc.needs_fix_threshold == 1


def test_assay_config_has_review() -> None:
    cfg = AssayConfig()
    assert hasattr(cfg, "review")
    assert isinstance(cfg.review, ReviewConfig)


def test_review_does_not_break_unknown_section_guard(tmp_path: Path) -> None:
    p = _write(tmp_path, "[notavalidsection]\nkey = 'val'\n")
    with pytest.raises(ConfigError, match="unknown config section"):
        load_config(str(p))
