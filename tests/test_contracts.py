"""Tests: the machine-readable agent contract manifest."""

from __future__ import annotations

import json
from pathlib import Path

from assay.contracts import build_manifest
from assay.contracts.manifest import TOOLS


def test_manifest_has_required_top_level_keys() -> None:
    m = build_manifest()
    for key in ("contract_version", "service", "auth", "tools", "endpoints", "payload_schema"):
        assert key in m
    assert m["service"] == "assay"


def test_every_tool_has_name_description_schema() -> None:
    for tool in TOOLS:
        assert tool["name"]
        assert tool["description"]
        assert tool["input_schema"]["type"] == "object"


def test_full_loop_tools_present() -> None:
    names = {t["name"] for t in TOOLS}
    expected = {
        "run_verification",
        "get_report",
        "get_status",
        "list_runs",
        "list_baselines",
        "approve_baseline",
        "reject_baseline",
        "set_baseline",
    }
    assert expected <= names


def test_committed_json_matches_module() -> None:
    """The on-disk tool_manifest.json must equal the module output (drift guard)."""
    json_path = Path(__file__).parent.parent / "src" / "assay" / "contracts" / "tool_manifest.json"
    on_disk = json.loads(json_path.read_text())
    assert on_disk == build_manifest()


def test_run_verification_requires_target_in_schema() -> None:
    tool = next(t for t in TOOLS if t["name"] == "run_verification")
    assert "target" in tool["input_schema"]["required"]
