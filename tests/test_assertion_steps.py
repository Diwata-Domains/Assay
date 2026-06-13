"""Tests for Playwright functional assertion steps (P25-T04)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from assay.runner.artifacts import collect_artifacts
from assay.runner.runner import RunResult
from assay.scripts.parser import ScriptParseError, parse_script

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _run_result(exit_code: int = 0) -> RunResult:
    return RunResult(exit_code=exit_code, output_dir="", stdout="", stderr="")


def _script_file(tmp_path: Path, steps: list[dict]) -> Path:
    p = tmp_path / "script.json"
    _write(p, {"name": "test", "steps": steps})
    return p


# ---------------------------------------------------------------------------
# Parser — new assertion step types accepted
# ---------------------------------------------------------------------------

def test_parser_accepts_expect_text(tmp_path):
    p = _script_file(tmp_path, [{"type": "expect_text", "selector": "#title", "text": "Hello"}])
    script = parse_script(p)
    assert script.steps[0].type == "expect_text"
    assert script.steps[0].selector == "#title"
    assert script.steps[0].text == "Hello"


def test_parser_accepts_expect_not_text(tmp_path):
    p = _script_file(tmp_path, [{"type": "expect_not_text", "selector": ".error", "text": "Error"}])
    script = parse_script(p)
    assert script.steps[0].type == "expect_not_text"
    assert script.steps[0].text == "Error"


def test_parser_accepts_expect_visible(tmp_path):
    p = _script_file(tmp_path, [{"type": "expect_visible", "selector": ".dashboard"}])
    script = parse_script(p)
    assert script.steps[0].type == "expect_visible"
    assert script.steps[0].selector == ".dashboard"


def test_parser_accepts_expect_url(tmp_path):
    p = _script_file(tmp_path, [{"type": "expect_url", "pattern": "/dashboard"}])
    script = parse_script(p)
    assert script.steps[0].type == "expect_url"
    assert script.steps[0].pattern == "/dashboard"


def test_parser_accepts_mixed_steps(tmp_path):
    p = _script_file(tmp_path, [
        {"type": "navigate", "url": "https://example.com"},
        {"type": "expect_text", "selector": "h1", "text": "Welcome"},
        {"type": "expect_url", "pattern": "example.com"},
        {"type": "screenshot", "label": "home"},
    ])
    script = parse_script(p)
    assert len(script.steps) == 4
    assert script.steps[1].type == "expect_text"
    assert script.steps[2].type == "expect_url"


# ---------------------------------------------------------------------------
# Parser — validation errors for new step types
# ---------------------------------------------------------------------------

def test_parser_expect_text_missing_selector_raises(tmp_path):
    p = _script_file(tmp_path, [{"type": "expect_text", "text": "Hello"}])
    with pytest.raises(ScriptParseError, match="selector"):
        parse_script(p)


def test_parser_expect_not_text_missing_selector_raises(tmp_path):
    p = _script_file(tmp_path, [{"type": "expect_not_text", "text": "Error"}])
    with pytest.raises(ScriptParseError, match="selector"):
        parse_script(p)


def test_parser_expect_visible_missing_selector_raises(tmp_path):
    p = _script_file(tmp_path, [{"type": "expect_visible"}])
    with pytest.raises(ScriptParseError, match="selector"):
        parse_script(p)


def test_parser_expect_url_missing_pattern_raises(tmp_path):
    p = _script_file(tmp_path, [{"type": "expect_url"}])
    with pytest.raises(ScriptParseError, match="pattern"):
        parse_script(p)


# ---------------------------------------------------------------------------
# Artifacts — expected/actual passthrough from script_result.json
# ---------------------------------------------------------------------------

def test_artifact_collector_passes_through_expected_actual(tmp_path):
    _write(tmp_path / "script_result.json", {
        "outcome": "fail", "name": "t", "url": "", "suite": "default",
        "timestamp": "", "error": None,
        "steps": [
            {
                "index": 0, "type": "expect_text", "label": "expect_text",
                "outcome": "fail", "error": 'Expected text "Hello" not found',
                "screenshot": None,
                "expected": "Hello",
                "actual": "Goodbye",
            },
        ],
    })
    bundle = collect_artifacts(str(tmp_path), _run_result(exit_code=1))
    step = bundle.steps[0]
    assert step.expected == "Hello"
    assert step.actual == "Goodbye"
    assert step.outcome == "fail"


def test_artifact_collector_no_expected_actual_for_non_assertion(tmp_path):
    _write(tmp_path / "script_result.json", {
        "outcome": "pass", "name": "t", "url": "", "suite": "default",
        "timestamp": "", "error": None,
        "steps": [
            {
                "index": 0, "type": "navigate", "label": "navigate",
                "outcome": "pass", "error": None, "screenshot": None,
            },
        ],
    })
    bundle = collect_artifacts(str(tmp_path), _run_result())
    step = bundle.steps[0]
    assert step.expected is None
    assert step.actual is None


def test_artifact_collector_passes_through_expect_visible(tmp_path):
    _write(tmp_path / "script_result.json", {
        "outcome": "fail", "name": "t", "url": "", "suite": "default",
        "timestamp": "", "error": None,
        "steps": [
            {
                "index": 0, "type": "expect_visible", "label": "expect_visible",
                "outcome": "fail", "error": 'Expected ".btn" to be visible',
                "screenshot": None,
                "expected": "visible",
                "actual": "not visible",
            },
        ],
    })
    bundle = collect_artifacts(str(tmp_path), _run_result(exit_code=1))
    assert bundle.steps[0].expected == "visible"
    assert bundle.steps[0].actual == "not visible"


# ---------------------------------------------------------------------------
# Formatter — expected/actual included in packet steps
# ---------------------------------------------------------------------------

def test_formatter_includes_expected_actual_when_set(tmp_path):
    from assay.formatter.formatter import format_packet

    _write(tmp_path / "script_result.json", {
        "outcome": "fail", "name": "t", "url": "", "suite": "default",
        "timestamp": "", "error": None,
        "steps": [
            {
                "index": 0, "type": "expect_url", "label": "expect_url",
                "outcome": "fail", "error": 'URL mismatch',
                "screenshot": None,
                "expected": 'contains "/dashboard"',
                "actual": "https://example.com/login",
            },
        ],
    })
    bundle = collect_artifacts(str(tmp_path), _run_result(exit_code=1))
    packet = format_packet(bundle)
    step_dict = packet["steps"][0]  # type: ignore[index]
    assert step_dict["expected"] == 'contains "/dashboard"'
    assert step_dict["actual"] == "https://example.com/login"


def test_formatter_omits_expected_actual_when_absent(tmp_path):
    from assay.formatter.formatter import format_packet

    _write(tmp_path / "script_result.json", {
        "outcome": "pass", "name": "t", "url": "", "suite": "default",
        "timestamp": "", "error": None,
        "steps": [
            {
                "index": 0, "type": "screenshot", "label": "home",
                "outcome": "pass", "error": None, "screenshot": None,
            },
        ],
    })
    bundle = collect_artifacts(str(tmp_path), _run_result())
    packet = format_packet(bundle)
    step_dict = packet["steps"][0]  # type: ignore[index]
    assert "expected" not in step_dict
    assert "actual" not in step_dict


# ---------------------------------------------------------------------------
# Console error detection — artifact passthrough
# ---------------------------------------------------------------------------

def test_console_error_step_has_error_message(tmp_path):
    _write(tmp_path / "script_result.json", {
        "outcome": "fail", "name": "t", "url": "", "suite": "default",
        "timestamp": "", "error": None,
        "steps": [
            {
                "index": 0, "type": "navigate", "label": "navigate",
                "outcome": "fail",
                "error": "console.error: Uncaught TypeError: Cannot read property 'x' of null",
                "screenshot": None,
            },
        ],
    })
    bundle = collect_artifacts(str(tmp_path), _run_result(exit_code=1))
    assert bundle.outcome == "fail"
    assert "console.error" in (bundle.steps[0].error or "")
