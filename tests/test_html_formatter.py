"""Unit tests for the HTML report formatter."""

from __future__ import annotations

import base64
from pathlib import Path

from assay.formatter.html_formatter import render_html


def _packet(
    outcome: str = "pass",
    verification_id: str = "abc-123",
    severity: str = "info",
    task_id: str | None = "TASK-0001",
    verified_at: str = "2026-04-28T10:00:00Z",
    summary: str = "test summary",
    artifact_refs: list[str] | None = None,
) -> dict[str, object]:
    return {
        "verification_id": verification_id,
        "task_id": task_id,
        "issue_type": "test_failure",
        "severity": severity,
        "outcome": outcome,
        "summary": summary,
        "artifact_refs": artifact_refs or [],
        "followup_candidates": [],
        "verified_at": verified_at,
    }


def test_returns_html_string() -> None:
    html = render_html([_packet()])
    assert html.strip().startswith("<!DOCTYPE html>")


def test_contains_summary_counts() -> None:
    packets = [_packet("pass"), _packet("fail"), _packet("inconclusive")]
    html = render_html(packets)
    assert "3" in html
    assert "1" in html


def test_outcome_values_present() -> None:
    html = render_html([_packet("pass"), _packet("fail")])
    assert "pass" in html
    assert "fail" in html


def test_verification_id_in_output() -> None:
    html = render_html([_packet(verification_id="deadbeef-0000-4000-8000-000000000001")])
    assert "deadbeef-0000-4000-8000-000000000001" in html


def test_summary_in_output() -> None:
    html = render_html([_packet(summary="navigation timeout on /checkout")])
    assert "navigation timeout on /checkout" in html


def test_screenshot_embedded_as_base64(tmp_path: Path) -> None:
    png = tmp_path / "shot.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    html = render_html([_packet(artifact_refs=[str(png)])])
    encoded = base64.b64encode(b"\x89PNG\r\n\x1a\n").decode()
    assert f"base64,{encoded}" in html


def test_missing_screenshot_skipped_gracefully() -> None:
    html = render_html([_packet(artifact_refs=["/nonexistent/path/screenshot.png"])])
    assert "base64" not in html
    assert "<img" not in html


def test_no_artifact_refs_no_img_tag() -> None:
    html = render_html([_packet(artifact_refs=[])])
    assert "<img" not in html


def test_empty_packet_list_renders() -> None:
    html = render_html([])
    assert "<!DOCTYPE html>" in html
    assert "0" in html


def test_task_id_none_renders_dash() -> None:
    html = render_html([_packet(task_id=None)])
    assert "—" in html


def test_no_external_resources() -> None:
    html = render_html([_packet()])
    assert "http://" not in html
    assert "https://" not in html
    assert "src=" not in html.split("<style>")[0] + html.split("</style>")[-1] or "<img" not in html or "data:" in html
