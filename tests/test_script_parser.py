"""Tests for the Assay script parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from assay.scripts.parser import AssayScript, ScriptParseError, ScriptStep, parse_script


def _write(tmp_path: Path, data: object) -> Path:
    p = tmp_path / "script.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ── valid scripts ──────────────────────────────────────────────────────────────

def test_parse_minimal_navigate(tmp_path):
    p = _write(tmp_path, {
        "name": "smoke",
        "steps": [{"type": "navigate", "url": "https://example.com"}],
    })
    s = parse_script(p)
    assert s.name == "smoke"
    assert len(s.steps) == 1
    assert s.steps[0].type == "navigate"
    assert s.steps[0].url == "https://example.com"


def test_parse_all_step_types(tmp_path):
    p = _write(tmp_path, {"name": "all", "steps": [
        {"type": "navigate",   "url": "https://example.com"},
        {"type": "click",      "selector": "#btn"},
        {"type": "fill",       "selector": "#email", "value": "a@b.com"},
        {"type": "wait_for",   "selector": ".loaded", "timeout": 3000},
        {"type": "wait",       "ms": 500},
        {"type": "screenshot", "label": "done"},
    ]})
    s = parse_script(p)
    assert len(s.steps) == 6
    assert s.steps[1].selector == "#btn"
    assert s.steps[2].value == "a@b.com"
    assert s.steps[3].timeout == 3000
    assert s.steps[4].ms == 500
    assert s.steps[5].label == "done"


def test_name_defaults_to_filename(tmp_path):
    p = tmp_path / "my-test.json"
    p.write_text(json.dumps({"steps": [{"type": "navigate", "url": "https://x.com"}]}))
    s = parse_script(p)
    assert s.name == "my-test"


def test_label_defaults_to_type(tmp_path):
    p = _write(tmp_path, {"name": "t", "steps": [{"type": "navigate", "url": "https://x.com"}]})
    s = parse_script(p)
    assert s.steps[0].label == "navigate"


def test_to_dict_roundtrip(tmp_path):
    p = _write(tmp_path, {
        "name": "rt",
        "steps": [
            {"type": "navigate", "url": "https://example.com"},
            {"type": "screenshot", "label": "home"},
        ],
    })
    s = parse_script(p)
    d = s.to_dict()
    assert d["name"] == "rt"
    assert len(d["steps"]) == 2
    assert d["steps"][0]["type"] == "navigate"


# ── invalid scripts ────────────────────────────────────────────────────────────

def test_error_not_a_dict(tmp_path):
    p = _write(tmp_path, ["not", "an", "object"])
    with pytest.raises(ScriptParseError, match="JSON object"):
        parse_script(p)


def test_error_empty_steps(tmp_path):
    p = _write(tmp_path, {"name": "t", "steps": []})
    with pytest.raises(ScriptParseError, match="empty"):
        parse_script(p)


def test_error_steps_not_array(tmp_path):
    p = _write(tmp_path, {"name": "t", "steps": "not-an-array"})
    with pytest.raises(ScriptParseError, match="array"):
        parse_script(p)


def test_error_unknown_step_type(tmp_path):
    p = _write(tmp_path, {"name": "t", "steps": [{"type": "hover", "selector": "#x"}]})
    with pytest.raises(ScriptParseError, match="unknown type"):
        parse_script(p)


def test_error_navigate_missing_url(tmp_path):
    p = _write(tmp_path, {"name": "t", "steps": [{"type": "navigate"}]})
    with pytest.raises(ScriptParseError, match="'url' is required"):
        parse_script(p)


def test_error_click_missing_selector(tmp_path):
    p = _write(tmp_path, {"name": "t", "steps": [{"type": "click"}]})
    with pytest.raises(ScriptParseError, match="'selector' is required"):
        parse_script(p)


def test_error_fill_missing_selector(tmp_path):
    p = _write(tmp_path, {"name": "t", "steps": [{"type": "fill", "value": "x"}]})
    with pytest.raises(ScriptParseError, match="'selector' is required"):
        parse_script(p)


def test_error_wait_for_missing_selector(tmp_path):
    p = _write(tmp_path, {"name": "t", "steps": [{"type": "wait_for"}]})
    with pytest.raises(ScriptParseError, match="'selector' is required"):
        parse_script(p)


def test_error_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{ not valid json", encoding="utf-8")
    with pytest.raises(ScriptParseError, match="failed to read"):
        parse_script(p)


def test_error_step_not_object(tmp_path):
    p = _write(tmp_path, {"name": "t", "steps": ["navigate", "click"]})
    with pytest.raises(ScriptParseError, match="must be an object"):
        parse_script(p)
