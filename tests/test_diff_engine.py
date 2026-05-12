"""Tests: pixel diff engine."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from assay.diff.engine import DiffError, DiffResult, diff_images


def _solid_png(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (10, 10)) -> Path:
    img = Image.new("RGB", size, color)
    img.save(str(path), "PNG")
    return path


def test_identical_images_zero_diff(tmp_path: Path) -> None:
    base = _solid_png(tmp_path / "base.png", (100, 150, 200))
    cand = _solid_png(tmp_path / "cand.png", (100, 150, 200))
    diff_path = tmp_path / "diff.png"
    result = diff_images(base, cand, diff_path)
    assert isinstance(result, DiffResult)
    assert result.changed_pixels == 0
    assert result.diff_pct == 0.0
    assert diff_path.exists()


def test_fully_different_images_nonzero_diff(tmp_path: Path) -> None:
    base = _solid_png(tmp_path / "base.png", (0, 0, 0))
    cand = _solid_png(tmp_path / "cand.png", (255, 255, 255))
    diff_path = tmp_path / "diff.png"
    result = diff_images(base, cand, diff_path)
    assert result.changed_pixels == 100
    assert result.total_pixels == 100
    assert result.diff_pct == 100.0


def test_partial_diff(tmp_path: Path) -> None:
    size = (10, 10)
    base_img = Image.new("RGB", size, (0, 0, 0))
    cand_img = Image.new("RGB", size, (0, 0, 0))
    for x in range(5):
        for y in range(10):
            cand_img.putpixel((x, y), (255, 255, 255))
    base_img.save(str(tmp_path / "base.png"), "PNG")
    cand_img.save(str(tmp_path / "cand.png"), "PNG")
    diff_path = tmp_path / "diff.png"
    result = diff_images(tmp_path / "base.png", tmp_path / "cand.png", diff_path)
    assert result.changed_pixels == 50
    assert result.total_pixels == 100
    assert result.diff_pct == 50.0


def test_diff_result_contains_path(tmp_path: Path) -> None:
    base = _solid_png(tmp_path / "base.png", (1, 2, 3))
    cand = _solid_png(tmp_path / "cand.png", (4, 5, 6))
    diff_path = tmp_path / "out_diff.png"
    result = diff_images(base, cand, diff_path)
    assert result.diff_image_path == str(diff_path)


def test_missing_baseline_raises(tmp_path: Path) -> None:
    cand = _solid_png(tmp_path / "cand.png", (0, 0, 0))
    with pytest.raises(DiffError, match="baseline not found"):
        diff_images(tmp_path / "nonexistent.png", cand, tmp_path / "diff.png")


def test_missing_candidate_raises(tmp_path: Path) -> None:
    base = _solid_png(tmp_path / "base.png", (0, 0, 0))
    with pytest.raises(DiffError, match="candidate not found"):
        diff_images(base, tmp_path / "nonexistent.png", tmp_path / "diff.png")


def test_diff_image_created_in_nested_dir(tmp_path: Path) -> None:
    base = _solid_png(tmp_path / "base.png", (10, 20, 30))
    cand = _solid_png(tmp_path / "cand.png", (30, 20, 10))
    diff_path = tmp_path / "sub" / "nested" / "diff.png"
    result = diff_images(base, cand, diff_path)
    assert Path(result.diff_image_path).exists()
