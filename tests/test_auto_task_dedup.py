"""Tests for auto-task deduplication (Phase 26 T04)."""

from __future__ import annotations

from pathlib import Path

from assay.config import AssayConfig, GrainConfig, OutputConfig
from assay.grain.auto_task import create_check_failure_task, create_regression_task


def _config(tmp_path: Path) -> AssayConfig:
    cfg = AssayConfig()
    cfg.grain = GrainConfig(
        repo=str(tmp_path / "grain-repo"),
        auto_create=True,
        output_path="assay-output",
    )
    cfg.output = OutputConfig(directory=str(tmp_path / "assay-output"))
    return cfg


# ---------------------------------------------------------------------------
# regression dedup
# ---------------------------------------------------------------------------


def test_regression_dedup_skips_second_write(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = create_regression_task(
        url="https://example.com",
        diff_pct=5.0,
        changed_pixels=900,
        total_pixels=18000,
        diff_image_path=None,
        config=cfg,
    )
    second = create_regression_task(
        url="https://example.com",
        diff_pct=6.0,
        changed_pixels=1100,
        total_pixels=18000,
        diff_image_path=None,
        config=cfg,
    )
    assert first is not None
    assert second is None


def test_regression_dedup_different_url_creates(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = create_regression_task(
        url="https://example.com/a",
        diff_pct=5.0,
        changed_pixels=900,
        total_pixels=18000,
        diff_image_path=None,
        config=cfg,
    )
    second = create_regression_task(
        url="https://example.com/b",
        diff_pct=5.0,
        changed_pixels=900,
        total_pixels=18000,
        diff_image_path=None,
        config=cfg,
    )
    assert first is not None
    assert second is not None


# ---------------------------------------------------------------------------
# check failure dedup
# ---------------------------------------------------------------------------


def test_check_dedup_skips_second_write(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = create_check_failure_task(
        check_id="ping",
        check_type="http",
        target="https://example.com",
        failed_assertions=[],
        error=None,
        config=cfg,
    )
    second = create_check_failure_task(
        check_id="ping",
        check_type="http",
        target="https://example.com",
        failed_assertions=[],
        error=None,
        config=cfg,
    )
    assert first is not None
    assert second is None


def test_check_dedup_different_check_id_creates(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = create_check_failure_task(
        check_id="ping",
        check_type="http",
        target="https://example.com",
        failed_assertions=[],
        error=None,
        config=cfg,
    )
    second = create_check_failure_task(
        check_id="cors",
        check_type="header",
        target="https://example.com",
        failed_assertions=[],
        error=None,
        config=cfg,
    )
    assert first is not None
    assert second is not None


def test_check_dedup_different_target_creates(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = create_check_failure_task(
        check_id="ping",
        check_type="http",
        target="https://example.com/a",
        failed_assertions=[],
        error=None,
        config=cfg,
    )
    second = create_check_failure_task(
        check_id="ping",
        check_type="http",
        target="https://example.com/b",
        failed_assertions=[],
        error=None,
        config=cfg,
    )
    assert first is not None
    assert second is not None


def test_dedup_survives_corrupt_json(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    dest_dir = Path(cfg.grain.repo) / cfg.grain.output_path
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "assay-bad.json").write_text("not json", encoding="utf-8")
    path = create_check_failure_task(
        check_id="ping",
        check_type="http",
        target="https://example.com",
        failed_assertions=[],
        error=None,
        config=cfg,
    )
    assert path is not None
