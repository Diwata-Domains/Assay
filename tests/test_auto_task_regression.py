"""Tests for auto Grain task creation on visual regression (Phase 26 T02)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from assay.config import AssayConfig, GrainConfig, OutputConfig
from assay.grain.auto_task import create_regression_task


def _config(tmp_path: Path, auto_create: bool = True, repo: str = "") -> AssayConfig:
    cfg = AssayConfig()
    cfg.grain = GrainConfig(
        repo=repo or str(tmp_path / "grain-repo"),
        auto_create=auto_create,
        output_path="assay-output",
    )
    cfg.output = OutputConfig(directory=str(tmp_path / "assay-output"))
    return cfg


# ---------------------------------------------------------------------------
# create_regression_task
# ---------------------------------------------------------------------------


def test_creates_packet_file_on_regression(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    path = create_regression_task(
        url="https://example.com",
        diff_pct=5.3,
        changed_pixels=1000,
        total_pixels=18888,
        diff_image_path=None,
        config=cfg,
    )
    assert path is not None
    assert Path(path).exists()


def test_packet_has_correct_fields(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    path = create_regression_task(
        url="https://example.com/login",
        diff_pct=2.1,
        changed_pixels=400,
        total_pixels=19000,
        diff_image_path=None,
        config=cfg,
    )
    assert path is not None
    data = json.loads(Path(path).read_text())
    assert data["issue_type"] == "visual_regression"
    assert data["outcome"] == "fail"
    assert data["severity"] == "error"
    assert "example.com/login" in data["summary"]
    assert data["diff_pct"] == pytest.approx(2.1)
    assert data["changed_pixels"] == 400
    assert data["total_pixels"] == 19000


def test_diff_image_in_artifact_refs(tmp_path: Path) -> None:
    diff_path = str(tmp_path / "diff.png")
    cfg = _config(tmp_path)
    path = create_regression_task(
        url="https://example.com",
        diff_pct=3.0,
        changed_pixels=500,
        total_pixels=16000,
        diff_image_path=diff_path,
        config=cfg,
    )
    assert path is not None
    data = json.loads(Path(path).read_text())
    assert diff_path in data["artifact_refs"]


def test_no_diff_image_gives_empty_refs(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    path = create_regression_task(
        url="https://example.com",
        diff_pct=1.0,
        changed_pixels=100,
        total_pixels=10000,
        diff_image_path=None,
        config=cfg,
    )
    assert path is not None
    data = json.loads(Path(path).read_text())
    assert data["artifact_refs"] == []


def test_returns_none_when_auto_create_false(tmp_path: Path) -> None:
    cfg = _config(tmp_path, auto_create=False)
    path = create_regression_task(
        url="https://example.com",
        diff_pct=10.0,
        changed_pixels=2000,
        total_pixels=20000,
        diff_image_path=None,
        config=cfg,
    )
    assert path is None


def test_returns_none_when_repo_empty(tmp_path: Path) -> None:
    cfg = AssayConfig()
    cfg.grain = GrainConfig(repo="", auto_create=True, output_path="assay-output")
    path = create_regression_task(
        url="https://example.com",
        diff_pct=10.0,
        changed_pixels=2000,
        total_pixels=20000,
        diff_image_path=None,
        config=cfg,
    )
    assert path is None


def test_packet_written_to_grain_repo(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    path = create_regression_task(
        url="https://example.com",
        diff_pct=5.0,
        changed_pixels=900,
        total_pixels=18000,
        diff_image_path=None,
        config=cfg,
    )
    assert path is not None
    expected_dir = Path(cfg.grain.repo) / cfg.grain.output_path
    assert Path(path).parent == expected_dir


# ---------------------------------------------------------------------------
# CLI --compare wires auto_create
# ---------------------------------------------------------------------------


def test_cli_compare_regression_creates_grain_task(tmp_path: Path) -> None:
    """assay run --compare with a regression creates a grain task when auto_create=True."""
    from unittest.mock import MagicMock, patch

    from typer.testing import CliRunner

    from assay.cli.main import app as cli_app

    db = tmp_path / "store.db"
    grain_repo = tmp_path / "grain-repo"
    cfg_path = tmp_path / "assay.toml"
    cfg_path.write_text(
        f"""
[project]
name = "test"
[output]
directory = "{tmp_path}/assay-output"
[store]
db = "{db}"
[keys]
store = "{tmp_path}/keys.json"
[schedule]
store = "{tmp_path}/schedules.json"
[grain]
repo = "{grain_repo}"
auto_create = true
output_path = "assay-output"
""",
        encoding="utf-8",
    )

    mock_diff_result = MagicMock()
    mock_diff_result.diff_pct = 8.0
    mock_diff_result.changed_pixels = 1500
    mock_diff_result.total_pixels = 18000
    mock_diff_result.diff_image_path = None

    with (
        patch("assay.cli.main._runner.run") as mock_run,
        patch("assay.cli.main._artifacts.collect_artifacts") as mock_collect,
        patch("assay.diff.engine.diff_images") as mock_diff,
        patch("assay.store.db.get_baseline_for_url") as mock_get_bl,
        patch("assay.store.db.init_db"),
        patch("assay.cli.main.shutil.copy2"),
        patch("assay.cli.main.write_packet", return_value=str(tmp_path / "assay-output" / "p.json")),
        patch("assay.cli.main._store_packet"),
    ):
        from assay.runner.runner import RunResult

        mock_run.return_value = RunResult(exit_code=0, output_dir=str(tmp_path), stdout="", stderr="")
        bundle = MagicMock()
        bundle.outcome = "pass"
        bundle.error = None
        bundle.screenshot_path = str(tmp_path / "shot.png")
        bundle.steps = []
        bundle.url = "https://example.com"
        mock_collect.return_value = bundle

        baseline_pkg = {"artifact_refs": [str(tmp_path / "baseline.png")]}
        mock_get_bl.return_value = baseline_pkg

        (tmp_path / "shot.png").write_bytes(b"png")
        (tmp_path / "baseline.png").write_bytes(b"png")

        mock_diff.return_value = mock_diff_result

        runner = CliRunner()
        result = runner.invoke(
            cli_app,
            [
                "--config", str(cfg_path),
                "run",
                "--target", "https://example.com",
                "--compare",
                "--threshold", "0.1",
                "--no-docker",
            ],
        )

    assert result.exit_code == 1
    grain_out = grain_repo / "assay-output"
    task_files = list(grain_out.glob("assay-*.json")) if grain_out.exists() else []
    assert len(task_files) == 1
    data = json.loads(task_files[0].read_text())
    assert data["issue_type"] == "visual_regression"
