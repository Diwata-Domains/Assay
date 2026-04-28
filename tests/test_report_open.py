"""Tests for assay report --open flag."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from assay.cli.main import app

runner = CliRunner()


def _write_packet(output_dir: Path, outcome: str = "pass") -> None:
    packet = {
        "verification_id": "aaaaaaaa-0000-4000-8000-000000000001",
        "task_id": None,
        "issue_type": "test_failure",
        "severity": "info",
        "outcome": outcome,
        "summary": f"{outcome}: https://example.com",
        "artifact_refs": [],
        "followup_candidates": [],
        "verified_at": "2026-04-28T10:00:00Z",
    }
    (output_dir / "assay-2026-test.json").write_text(json.dumps(packet))


def test_open_flag_calls_webbrowser(tmp_path: Path) -> None:
    _write_packet(tmp_path)
    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(app, ["report", "--output", str(tmp_path), "--format", "html", "--open"])
    assert result.exit_code == 0
    mock_open.assert_called_once()
    call_arg = mock_open.call_args[0][0]
    assert call_arg.endswith("assay-report.html")
    assert call_arg.startswith("file://")


def test_open_flag_path_matches_printed_path(tmp_path: Path) -> None:
    _write_packet(tmp_path)
    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(app, ["report", "--output", str(tmp_path), "--format", "html", "--open"])
    assert result.exit_code == 0
    printed_path = result.output.strip().replace("report: ", "")
    call_arg = mock_open.call_args[0][0]
    assert call_arg == f"file://{printed_path}"


def test_open_without_html_format_warns(tmp_path: Path) -> None:
    _write_packet(tmp_path)
    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(app, ["report", "--output", str(tmp_path), "--format", "text", "--open"])
    assert result.exit_code == 0
    assert "--open is only supported with --format html" in result.output
    mock_open.assert_not_called()


def test_open_without_html_format_json_warns(tmp_path: Path) -> None:
    _write_packet(tmp_path)
    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(app, ["report", "--output", str(tmp_path), "--format", "json", "--open"])
    assert result.exit_code == 0
    assert "--open is only supported with --format html" in result.output
    mock_open.assert_not_called()


def test_html_without_open_does_not_call_webbrowser(tmp_path: Path) -> None:
    _write_packet(tmp_path)
    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(app, ["report", "--output", str(tmp_path), "--format", "html"])
    assert result.exit_code == 0
    mock_open.assert_not_called()
