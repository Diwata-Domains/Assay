"""Pixel-level diff engine: compare two PNG screenshots and produce a highlighted diff image."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class DiffError(Exception):
    """Raised when diff inputs are missing or unreadable."""


@dataclass
class DiffResult:
    changed_pixels: int
    total_pixels: int
    diff_pct: float
    diff_image_path: str


def diff_images(baseline_path: Path, candidate_path: Path, diff_path: Path) -> DiffResult:
    """Compare baseline and candidate screenshots pixel-by-pixel.

    Saves a diff image (unchanged pixels dimmed, changed pixels highlighted red) to diff_path.
    Raises DiffError if either input file is missing.
    """
    from PIL import Image, ImageChops, ImageEnhance

    if not baseline_path.exists():
        raise DiffError(f"baseline not found: {baseline_path}")
    if not candidate_path.exists():
        raise DiffError(f"candidate not found: {candidate_path}")

    base = Image.open(baseline_path).convert("RGB")
    cand = Image.open(candidate_path).convert("RGB")

    if base.size != cand.size:
        cand = cand.resize(base.size, Image.Resampling.LANCZOS)

    width, height = base.size
    total_pixels = width * height

    diff = ImageChops.difference(base, cand)
    diff_gray = diff.convert("L")

    histogram = diff_gray.histogram()
    unchanged = histogram[0] if histogram else 0
    changed = total_pixels - unchanged

    mask = diff_gray.point(lambda v: 255 if v > 0 else 0)
    dimmed = ImageEnhance.Brightness(cand).enhance(0.6).convert("RGB")
    red = Image.new("RGB", base.size, (220, 50, 50))
    output = Image.composite(red, dimmed, mask)

    diff_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(str(diff_path), "PNG")

    diff_pct = round(changed / total_pixels * 100, 4) if total_pixels > 0 else 0.0
    return DiffResult(
        changed_pixels=changed,
        total_pixels=total_pixels,
        diff_pct=diff_pct,
        diff_image_path=str(diff_path),
    )
