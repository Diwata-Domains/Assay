"""Tests for auto Grain task creation on check failure (Phase 26 T03)."""

from __future__ import annotations

import json
from pathlib import Path

from assay.config import AssayConfig, GrainConfig, OutputConfig
from assay.grain.auto_task import create_check_failure_task


def _config(tmp_path: Path, auto_create: bool = True) -> AssayConfig:
    cfg = AssayConfig()
    cfg.grain = GrainConfig(
        repo=str(tmp_path / "grain-repo"),
        auto_create=auto_create,
        output_path="assay-output",
    )
    cfg.output = OutputConfig(directory=str(tmp_path / "assay-output"))
    return cfg


# ---------------------------------------------------------------------------
# create_check_failure_task
# ---------------------------------------------------------------------------


def test_creates_packet_for_failed_check(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    path = create_check_failure_task(
        check_id="api-health",
        check_type="http",
        target="https://api.example.com/health",
        failed_assertions=[{"name": "status_code", "expected": "200", "actual": "503"}],
        error=None,
        config=cfg,
    )
    assert path is not None
    assert Path(path).exists()


def test_packet_fields(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    path = create_check_failure_task(
        check_id="cors-check",
        check_type="header",
        target="https://api.example.com",
        failed_assertions=[
            {"name": "expect_header", "expected": "access-control-allow-origin", "actual": "absent"}
        ],
        error=None,
        config=cfg,
    )
    assert path is not None
    data = json.loads(Path(path).read_text())
    assert data["issue_type"] == "check_failure"
    assert data["outcome"] == "fail"
    assert data["severity"] == "error"
    assert "cors-check" in data["summary"]
    assert data["check_id"] == "cors-check"
    assert data["check_type"] == "header"
    assert "api.example.com" in data["target"]


def test_packet_detail_contains_assertion(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    path = create_check_failure_task(
        check_id="ping",
        check_type="http",
        target="https://example.com",
        failed_assertions=[{"name": "status_code", "expected": "200", "actual": "404"}],
        error=None,
        config=cfg,
    )
    assert path is not None
    data = json.loads(Path(path).read_text())
    assert "status_code" in data["detail"]
    assert "404" in data["detail"]


def test_packet_includes_error_field(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    path = create_check_failure_task(
        check_id="ping",
        check_type="http",
        target="https://example.com",
        failed_assertions=[],
        error="connection refused",
        config=cfg,
    )
    assert path is not None
    data = json.loads(Path(path).read_text())
    assert data.get("error") == "connection refused"


def test_returns_none_when_auto_create_false(tmp_path: Path) -> None:
    cfg = _config(tmp_path, auto_create=False)
    path = create_check_failure_task(
        check_id="ping",
        check_type="http",
        target="https://example.com",
        failed_assertions=[],
        error=None,
        config=cfg,
    )
    assert path is None


def test_written_to_grain_repo(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    path = create_check_failure_task(
        check_id="ping",
        check_type="http",
        target="https://example.com",
        failed_assertions=[],
        error=None,
        config=cfg,
    )
    assert path is not None
    expected_dir = Path(cfg.grain.repo) / cfg.grain.output_path
    assert Path(path).parent == expected_dir


# ---------------------------------------------------------------------------
# CLI check_cmd wires auto_create
# ---------------------------------------------------------------------------


def test_check_cmd_creates_grain_task_on_failure(tmp_path: Path) -> None:
    from unittest.mock import patch

    from typer.testing import CliRunner

    from assay.cli.main import app as cli_app

    grain_repo = tmp_path / "grain-repo"
    db = tmp_path / "store.db"
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

[[checks]]
id = "ping"
type = "http"
target = "https://example.com"
expect_status = 200
""",
        encoding="utf-8",
    )

    from assay.checks.models import AssertionResult, CheckResult

    failing = CheckResult(
        check_id="ping",
        check_type="http",
        target="https://example.com",
        passed=False,
        assertions=[AssertionResult(name="status_code", passed=False, expected="200", actual="503")],
        checked_at="2026-06-13T00:00:00Z",
    )

    with (
        patch("assay.checks.runner.run_check", return_value=failing),
        patch("assay.store.db.init_db"),
        patch("assay.store.db.insert_check_result"),
    ):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["--config", str(cfg_path), "check"])

    assert result.exit_code == 1
    grain_out = grain_repo / "assay-output"
    task_files = list(grain_out.glob("assay-*.json")) if grain_out.exists() else []
    assert len(task_files) == 1
    data = json.loads(task_files[0].read_text())
    assert data["issue_type"] == "check_failure"


def test_check_cmd_no_grain_task_on_pass(tmp_path: Path) -> None:
    from unittest.mock import patch

    from typer.testing import CliRunner

    from assay.cli.main import app as cli_app

    grain_repo = tmp_path / "grain-repo"
    db = tmp_path / "store.db"
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

[[checks]]
id = "ping"
type = "http"
target = "https://example.com"
expect_status = 200
""",
        encoding="utf-8",
    )

    from assay.checks.models import AssertionResult, CheckResult

    passing = CheckResult(
        check_id="ping",
        check_type="http",
        target="https://example.com",
        passed=True,
        assertions=[AssertionResult(name="status_code", passed=True, expected="200", actual="200")],
        checked_at="2026-06-13T00:00:00Z",
    )

    with (
        patch("assay.checks.runner.run_check", return_value=passing),
        patch("assay.store.db.init_db"),
        patch("assay.store.db.insert_check_result"),
    ):
        runner = CliRunner()
        result = runner.invoke(cli_app, ["--config", str(cfg_path), "check"])

    assert result.exit_code == 0
    grain_out = grain_repo / "assay-output"
    task_files = list(grain_out.glob("assay-*.json")) if grain_out.exists() else []
    assert len(task_files) == 0
