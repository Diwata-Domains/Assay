"""Tests for `assay report` command (P11-T03)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from assay.cli.main import app

runner = CliRunner()


def _write_packet(directory: Path, overrides: dict | None = None) -> dict:
    base: dict = {
        "verification_id": "aabbccdd-0000-0000-0000-000000000001",
        "task_id": None,
        "issue_type": "test_failure",
        "severity": "info",
        "outcome": "pass",
        "summary": "pass: https://example.com",
        "artifact_refs": [],
        "followup_candidates": [],
        "verified_at": "2026-04-21T10:00:00Z",
    }
    if overrides:
        base.update(overrides)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"assay-20260421100000Z-{base['verification_id']}.json"
    path.write_text(json.dumps(base))
    return base


def test_report_renders_table(tmp_path: Path) -> None:
    _write_packet(tmp_path)
    result = runner.invoke(app, ["report", "--output", str(tmp_path)])
    assert result.exit_code == 0
    assert "pass" in result.output
    assert "aabbccdd" in result.output


def test_report_no_packets(tmp_path: Path) -> None:
    result = runner.invoke(app, ["report", "--output", str(tmp_path)])
    assert result.exit_code == 0
    assert "no packets found" in result.output


def test_report_missing_dir(tmp_path: Path) -> None:
    result = runner.invoke(app, ["report", "--output", str(tmp_path / "nonexistent")])
    assert result.exit_code == 1


def test_report_json_format(tmp_path: Path) -> None:
    _write_packet(tmp_path)
    result = runner.invoke(app, ["report", "--output", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list) and len(data) == 1
    assert data[0]["outcome"] == "pass"


def test_report_json_multiple_packets(tmp_path: Path) -> None:
    _write_packet(tmp_path, {"verification_id": "aabbccdd-0000-0000-0000-000000000001", "outcome": "pass"})
    _write_packet(tmp_path, {"verification_id": "aabbccdd-0000-0000-0000-000000000002", "outcome": "fail"})
    result = runner.invoke(app, ["report", "--output", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


def test_report_filter_outcome_fail(tmp_path: Path) -> None:
    _write_packet(tmp_path, {"verification_id": "aabbccdd-0000-0000-0000-000000000001", "outcome": "pass"})
    _write_packet(tmp_path, {"verification_id": "aabbccdd-0000-0000-0000-000000000002", "outcome": "fail"})
    result = runner.invoke(app, ["report", "--output", str(tmp_path), "--filter", "outcome=fail"])
    assert result.exit_code == 0
    assert "fail" in result.output
    # pass row should be excluded
    assert "aabbccdd-0000-0000-0000-000000000001" not in result.output


def test_report_filter_no_match(tmp_path: Path) -> None:
    _write_packet(tmp_path)
    result = runner.invoke(app, ["report", "--output", str(tmp_path), "--filter", "outcome=fail"])
    assert result.exit_code == 0
    assert "no packets found" in result.output


def test_report_filter_invalid_form(tmp_path: Path) -> None:
    _write_packet(tmp_path)
    result = runner.invoke(app, ["report", "--output", str(tmp_path), "--filter", "badfilter"])
    assert result.exit_code == 2


def test_report_screenshot_indicator_yes(tmp_path: Path) -> None:
    vid = "aabbccdd-0000-0000-0000-000000000001"
    png = tmp_path / f"{vid}.png"
    png.write_bytes(b"PNG")
    _write_packet(tmp_path, {"verification_id": vid, "artifact_refs": [str(png)]})
    result = runner.invoke(app, ["report", "--output", str(tmp_path)])
    assert result.exit_code == 0
    assert "yes" in result.output


def test_report_screenshot_indicator_no(tmp_path: Path) -> None:
    _write_packet(tmp_path, {"artifact_refs": []})
    result = runner.invoke(app, ["report", "--output", str(tmp_path)])
    assert result.exit_code == 0
    assert "no" in result.output
