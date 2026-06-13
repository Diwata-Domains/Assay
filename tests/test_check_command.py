"""Tests for assay check command and [checks] config (P25-T01)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from assay.checks.models import AssertionResult, CheckResult
from assay.cli.main import app
from assay.config import ConfigError, _parse
from assay.store.db import init_db, list_check_results

runner = CliRunner()


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------

def test_parse_checks_empty():
    cfg = _parse({})
    assert cfg.checks == []


def test_parse_checks_http():
    raw = {
        "checks": [
            {
                "id": "health",
                "type": "http",
                "target": "https://example.com/health",
                "expect_status": 200,
                "max_response_ms": 500,
            }
        ]
    }
    cfg = _parse(raw)
    assert len(cfg.checks) == 1
    c = cfg.checks[0]
    assert c.id == "health"
    assert c.type == "http"
    assert c.target == "https://example.com/health"
    assert c.expect_status == 200
    assert c.max_response_ms == 500


def test_parse_checks_all_fields():
    raw = {
        "checks": [
            {
                "id": "cors",
                "type": "header",
                "target": "https://api.example.com",
                "expect_header": "Access-Control-Allow-Origin",
                "expect_value": "*",
                "timeout_seconds": 5,
            }
        ]
    }
    cfg = _parse(raw)
    c = cfg.checks[0]
    assert c.expect_header == "Access-Control-Allow-Origin"
    assert c.expect_value == "*"
    assert c.timeout_seconds == 5


def test_parse_checks_missing_id_raises():
    raw = {"checks": [{"type": "http", "target": "https://x.com"}]}
    with pytest.raises(ConfigError, match="missing required field: id"):
        _parse(raw)


def test_parse_checks_missing_type_raises():
    raw = {"checks": [{"id": "x", "target": "https://x.com"}]}
    with pytest.raises(ConfigError, match="missing required field: type"):
        _parse(raw)


def test_parse_checks_missing_target_raises():
    raw = {"checks": [{"id": "x", "type": "http"}]}
    with pytest.raises(ConfigError, match="missing required field: target"):
        _parse(raw)


def test_parse_checks_invalid_status_raises():
    raw = {"checks": [{"id": "x", "type": "http", "target": "https://x.com", "expect_status": "200"}]}
    with pytest.raises(ConfigError, match="expect_status must be an integer"):
        _parse(raw)


def test_parse_checks_not_array_raises():
    raw = {"checks": {"id": "x"}}
    with pytest.raises(ConfigError, match="array-of-tables"):
        _parse(raw)


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

def test_insert_and_list_check_results(tmp_path):
    db = tmp_path / "store.db"
    init_db(db)
    from assay.store.db import insert_check_result
    result = {
        "check_id": "health",
        "check_type": "http",
        "target": "https://example.com",
        "passed": True,
        "assertions": [{"name": "status_code", "passed": True, "expected": "200", "actual": "200"}],
        "error": None,
        "checked_at": "2026-06-13T00:00:00+00:00",
    }
    insert_check_result(result, db)
    rows = list_check_results(db)
    assert len(rows) == 1
    assert rows[0]["check_id"] == "health"
    assert rows[0]["passed"] is True
    assert rows[0]["assertions"][0]["name"] == "status_code"


# ---------------------------------------------------------------------------
# CLI dispatch — uses real config file (same pattern as test_report_command.py)
# ---------------------------------------------------------------------------


def _write_toml(tmp_path: Path, checks_toml: str = "") -> tuple[Path, Path]:
    db = tmp_path / "store.db"
    cfg = tmp_path / "assay.toml"
    cfg.write_text(f'[store]\ndb = "{db}"\n{checks_toml}', encoding="utf-8")
    return cfg, db


def test_check_cmd_no_checks_exits_0(tmp_path):
    cfg, _ = _write_toml(tmp_path)
    result = runner.invoke(app, ["--config", str(cfg), "check"])
    assert result.exit_code == 0
    assert "no checks configured" in result.output


def test_check_cmd_unknown_id_exits_2(tmp_path):
    cfg, _ = _write_toml(tmp_path, '[[checks]]\nid="health"\ntype="http"\ntarget="https://x.com"\n')
    result = runner.invoke(app, ["--config", str(cfg), "check", "--check", "nonexistent"])
    assert result.exit_code == 2


def test_check_cmd_passing_exits_0(tmp_path):
    cfg, _ = _write_toml(
        tmp_path,
        '[[checks]]\nid="health"\ntype="http"\ntarget="https://x.com"\nexpect_status=200\n',
    )
    mock_result = CheckResult(
        check_id="health",
        check_type="http",
        target="https://x.com",
        passed=True,
        assertions=[AssertionResult("status_code", True, "200", "200")],
        checked_at="2026-06-13T00:00:00+00:00",
    )
    with patch("assay.checks.runner.run_check", return_value=mock_result):
        result = runner.invoke(app, ["--config", str(cfg), "check"])
    assert result.exit_code == 0
    assert "PASS" in result.output


def test_check_cmd_failing_exits_1(tmp_path):
    cfg, _ = _write_toml(
        tmp_path,
        '[[checks]]\nid="health"\ntype="http"\ntarget="https://x.com"\nexpect_status=200\n',
    )
    mock_result = CheckResult(
        check_id="health",
        check_type="http",
        target="https://x.com",
        passed=False,
        assertions=[AssertionResult("status_code", False, "200", "500")],
        checked_at="2026-06-13T00:00:00+00:00",
    )
    with patch("assay.checks.runner.run_check", return_value=mock_result):
        result = runner.invoke(app, ["--config", str(cfg), "check"])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_check_cmd_single_id_filter(tmp_path):
    toml = (
        '[[checks]]\nid="health"\ntype="http"\ntarget="https://x.com"\n'
        '[[checks]]\nid="cors"\ntype="header"\ntarget="https://api.x.com"\n'
    )
    cfg, _ = _write_toml(tmp_path, toml)
    mock_result = CheckResult(
        check_id="health",
        check_type="http",
        target="https://x.com",
        passed=True,
        checked_at="2026-06-13T00:00:00+00:00",
    )
    with patch("assay.checks.runner.run_check", return_value=mock_result) as mock_run:
        result = runner.invoke(app, ["--config", str(cfg), "check", "--check", "health"])
    assert mock_run.call_count == 1
    called_check = mock_run.call_args[0][0]
    assert called_check.id == "health"
    assert result.exit_code == 0


def test_check_cmd_unknown_type_exits_2(tmp_path):
    from assay.checks.runner import UnknownCheckType
    cfg, _ = _write_toml(tmp_path, '[[checks]]\nid="mystery"\ntype="unsupported"\ntarget="https://x.com"\n')
    with patch("assay.checks.runner.run_check", side_effect=UnknownCheckType("unsupported check type: 'unsupported'")):
        result = runner.invoke(app, ["--config", str(cfg), "check"])
    assert result.exit_code == 2


def test_check_cmd_stores_result(tmp_path):
    cfg, db = _write_toml(
        tmp_path,
        '[[checks]]\nid="health"\ntype="http"\ntarget="https://x.com"\n',
    )
    mock_result = CheckResult(
        check_id="health",
        check_type="http",
        target="https://x.com",
        passed=True,
        checked_at="2026-06-13T00:00:00+00:00",
    )
    with patch("assay.checks.runner.run_check", return_value=mock_result):
        runner.invoke(app, ["--config", str(cfg), "check"])

    rows = list_check_results(db)
    assert len(rows) == 1
    assert rows[0]["check_id"] == "health"
    assert rows[0]["passed"] is True
