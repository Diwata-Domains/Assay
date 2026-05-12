"""Tests: assay run --compare flag — pixel diff against stored baseline."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image
from typer.testing import CliRunner

from assay.cli.main import app
from assay.store.db import init_db, list_packets, set_baseline

cli = CliRunner(env={"NO_COLOR": "1"})

_URL = "https://example.com/page"

_RESULT_JSON = json.dumps(
    {
        "outcome": "pass",
        "url": _URL,
        "suite": "default",
        "timestamp": "2026-05-01T10:00:00Z",
        "error": None,
    }
)


def _solid_png(path: Path, color: tuple[int, int, int]) -> None:
    img = Image.new("RGB", (10, 10), color)
    img.save(str(path), "PNG")


def _fake_run(output_dir: str, color: tuple[int, int, int]):
    """Factory: returns a fake subprocess.run that writes result.json + screenshot.png."""

    def _inner(cmd, **kwargs):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        (Path(output_dir) / "result.json").write_text(_RESULT_JSON)
        _solid_png(Path(output_dir) / "screenshot.png", color)
        r = MagicMock(spec=subprocess.CompletedProcess)
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    return _inner


def _first_run_and_set_baseline(tmp_path: Path) -> tuple[Path, Path]:
    """Run once, set the packet as baseline. Returns (output_dir, db_path)."""
    output_dir = tmp_path / "output"
    db_path = tmp_path / "store.db"
    init_db(db_path)

    with patch("subprocess.run", side_effect=_fake_run(str(output_dir), (0, 0, 0))):
        result = cli.invoke(
            app,
            [
                "--config", str(tmp_path / "assay.toml"),
                "run",
                "--target", _URL,
                "--output", str(output_dir),
            ],
            catch_exceptions=False,
        )
    assert result.exit_code == 0, result.output

    packets = list_packets(db_path)
    if not packets:
        ingest_db = Path.home() / ".assay" / "store.db"
        packets = list_packets(ingest_db)
    assert packets, "no packet found after first run"
    set_baseline(str(packets[-1]["verification_id"]), db_path)

    return output_dir, db_path


def _run_with_compare(
    tmp_path: Path,
    output_dir: Path,
    db_path: Path,
    color: tuple[int, int, int],
    threshold: float = 0.1,
):
    with patch("subprocess.run", side_effect=_fake_run(str(output_dir), color)):
        return cli.invoke(
            app,
            [
                "--config", str(tmp_path / "assay.toml"),
                "run",
                "--target", _URL,
                "--output", str(output_dir),
                "--compare",
                "--threshold", str(threshold),
            ],
            catch_exceptions=False,
        )


def _make_config(tmp_path: Path, db_path: Path) -> None:
    (tmp_path / "assay.toml").write_text(
        f"[store]\ndb = \"{db_path}\"\n"
        f"[output]\ndirectory = \"{tmp_path / 'output'}\"\n"
    )


def test_compare_no_baseline_exits_0(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    db_path = tmp_path / "store.db"
    init_db(db_path)
    _make_config(tmp_path, db_path)

    with patch("subprocess.run", side_effect=_fake_run(str(output_dir), (100, 100, 100))):
        result = cli.invoke(
            app,
            [
                "--config", str(tmp_path / "assay.toml"),
                "run",
                "--target", _URL,
                "--output", str(output_dir),
                "--compare",
            ],
            catch_exceptions=False,
        )
    assert result.exit_code == 0
    assert "no baseline" in result.output


def test_compare_identical_images_exits_0(tmp_path: Path) -> None:
    db_path = tmp_path / "store.db"
    _make_config(tmp_path, db_path)
    output_dir, _ = _first_run_and_set_baseline(tmp_path)
    (tmp_path / "assay.toml").write_text(
        f"[store]\ndb = \"{db_path}\"\n"
        f"[output]\ndirectory = \"{output_dir}\"\n"
    )

    result = _run_with_compare(tmp_path, output_dir, db_path, color=(0, 0, 0))
    assert result.exit_code == 0
    assert "diff:" in result.output
    assert "clean" in result.output


def test_compare_different_images_exits_1(tmp_path: Path) -> None:
    db_path = tmp_path / "store.db"
    _make_config(tmp_path, db_path)
    output_dir, _ = _first_run_and_set_baseline(tmp_path)
    (tmp_path / "assay.toml").write_text(
        f"[store]\ndb = \"{db_path}\"\n"
        f"[output]\ndirectory = \"{output_dir}\"\n"
    )

    result = _run_with_compare(tmp_path, output_dir, db_path, color=(255, 255, 255), threshold=0.1)
    assert result.exit_code == 1
    assert "REGRESSION" in result.output or "regression" in result.output.lower()


def test_compare_output_shows_diff_stats(tmp_path: Path) -> None:
    db_path = tmp_path / "store.db"
    _make_config(tmp_path, db_path)
    output_dir, _ = _first_run_and_set_baseline(tmp_path)
    (tmp_path / "assay.toml").write_text(
        f"[store]\ndb = \"{db_path}\"\n"
        f"[output]\ndirectory = \"{output_dir}\"\n"
    )

    result = _run_with_compare(tmp_path, output_dir, db_path, color=(255, 0, 0))
    assert "diff:" in result.output
    assert "pixels" in result.output


def test_compare_high_threshold_passes_regression(tmp_path: Path) -> None:
    db_path = tmp_path / "store.db"
    _make_config(tmp_path, db_path)
    output_dir, _ = _first_run_and_set_baseline(tmp_path)
    (tmp_path / "assay.toml").write_text(
        f"[store]\ndb = \"{db_path}\"\n"
        f"[output]\ndirectory = \"{output_dir}\"\n"
    )

    result = _run_with_compare(tmp_path, output_dir, db_path, color=(255, 255, 255), threshold=100.0)
    assert result.exit_code == 0
    assert "clean" in result.output
