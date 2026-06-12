"""Tests for script-mode artifact collection."""

from __future__ import annotations

import json
from pathlib import Path

from assay.runner.artifacts import ArtifactBundle, StepResult, collect_artifacts
from assay.runner.runner import RunResult


def _run_result(exit_code: int = 0, output_dir: str = "") -> RunResult:
    return RunResult(exit_code=exit_code, output_dir=output_dir)


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


# ── script_result.json present ────────────────────────────────────────────────

def test_collects_script_result(tmp_path):
    _write(tmp_path / "script_result.json", {
        "outcome": "pass",
        "name": "Login flow",
        "url": "https://example.com",
        "suite": "default",
        "timestamp": "2026-06-12T00:00:00Z",
        "error": None,
        "steps": [
            {"index": 0, "type": "navigate", "label": "navigate", "outcome": "pass", "error": None, "screenshot": None},
            {"index": 1, "type": "screenshot", "label": "homepage", "outcome": "pass", "error": None, "screenshot": "step-1-homepage.png"},
        ],
    })
    (tmp_path / "step-1-homepage.png").write_bytes(b"PNG")

    bundle = collect_artifacts(str(tmp_path), _run_result())
    assert bundle.outcome == "pass"
    assert bundle.script_name == "Login flow"
    assert len(bundle.steps) == 2
    assert bundle.steps[1].screenshot_path is not None
    assert bundle.steps[1].label == "homepage"


def test_script_result_sets_first_screenshot_on_bundle(tmp_path):
    _write(tmp_path / "script_result.json", {
        "outcome": "pass", "name": "t", "url": "", "suite": "default",
        "timestamp": "", "error": None,
        "steps": [
            {"index": 0, "type": "screenshot", "label": "s1", "outcome": "pass", "error": None, "screenshot": "step-0-s1.png"},
        ],
    })
    (tmp_path / "step-0-s1.png").write_bytes(b"PNG")
    bundle = collect_artifacts(str(tmp_path), _run_result())
    assert bundle.screenshot_path is not None
    assert "step-0-s1.png" in bundle.screenshot_path


def test_script_result_fail_outcome(tmp_path):
    _write(tmp_path / "script_result.json", {
        "outcome": "fail", "name": "t", "url": "", "suite": "default",
        "timestamp": "", "error": "selector not found",
        "steps": [
            {"index": 0, "type": "click", "label": "click", "outcome": "fail", "error": "selector not found", "screenshot": None},
        ],
    })
    bundle = collect_artifacts(str(tmp_path), _run_result(exit_code=1))
    assert bundle.outcome == "fail"
    assert bundle.steps[0].error == "selector not found"


def test_script_result_takes_precedence_over_result_json(tmp_path):
    _write(tmp_path / "result.json", {"outcome": "pass", "url": "", "suite": "default", "timestamp": "", "error": None})
    _write(tmp_path / "script_result.json", {
        "outcome": "fail", "name": "s", "url": "", "suite": "default",
        "timestamp": "", "error": None, "steps": [],
    })
    bundle = collect_artifacts(str(tmp_path), _run_result())
    assert bundle.outcome == "fail"
    assert bundle.script_name == "s"


def test_missing_screenshot_file_handled_gracefully(tmp_path):
    _write(tmp_path / "script_result.json", {
        "outcome": "pass", "name": "t", "url": "", "suite": "default",
        "timestamp": "", "error": None,
        "steps": [
            {"index": 0, "type": "screenshot", "label": "s", "outcome": "pass", "error": None, "screenshot": "missing.png"},
        ],
    })
    bundle = collect_artifacts(str(tmp_path), _run_result())
    assert bundle.steps[0].screenshot_path is None


# ── formatter integration ──────────────────────────────────────────────────────

def test_format_packet_includes_steps(tmp_path):
    from assay.formatter.formatter import format_packet

    _write(tmp_path / "script_result.json", {
        "outcome": "pass", "name": "Login flow", "url": "https://example.com",
        "suite": "default", "timestamp": "2026-06-12T00:00:00Z", "error": None,
        "steps": [
            {"index": 0, "type": "navigate", "label": "navigate", "outcome": "pass", "error": None, "screenshot": None},
            {"index": 1, "type": "screenshot", "label": "home", "outcome": "pass", "error": None, "screenshot": "step-1-home.png"},
        ],
    })
    (tmp_path / "step-1-home.png").write_bytes(b"PNG")
    bundle = collect_artifacts(str(tmp_path), _run_result())
    packet = format_packet(bundle)
    assert "steps" in packet
    assert packet["script_name"] == "Login flow"
    assert len(packet["steps"]) == 2
    assert packet["steps"][1]["label"] == "home"


def test_format_packet_no_steps_for_url_mode(tmp_path):
    from assay.formatter.formatter import format_packet

    _write(tmp_path / "result.json", {
        "outcome": "pass", "url": "https://example.com",
        "suite": "default", "timestamp": "2026-06-12T00:00:00Z", "error": None,
    })
    bundle = collect_artifacts(str(tmp_path), _run_result())
    packet = format_packet(bundle)
    assert "steps" not in packet


def test_step_screenshots_in_artifact_refs(tmp_path):
    from assay.formatter.formatter import format_packet

    _write(tmp_path / "script_result.json", {
        "outcome": "pass", "name": "t", "url": "", "suite": "default",
        "timestamp": "", "error": None,
        "steps": [
            {"index": 0, "type": "screenshot", "label": "a", "outcome": "pass", "error": None, "screenshot": "step-0-a.png"},
            {"index": 1, "type": "screenshot", "label": "b", "outcome": "pass", "error": None, "screenshot": "step-1-b.png"},
        ],
    })
    (tmp_path / "step-0-a.png").write_bytes(b"PNG")
    (tmp_path / "step-1-b.png").write_bytes(b"PNG")
    bundle = collect_artifacts(str(tmp_path), _run_result())
    packet = format_packet(bundle)
    refs = packet["artifact_refs"]
    assert len(refs) == 2
