"""Schema validation tests — verifies format_packet output conforms to the Grain Sentinel payload schema."""

from __future__ import annotations

import jsonschema
import pytest

from assay.formatter.formatter import format_packet
from assay.runner.artifacts import ArtifactBundle
from assay.schemas import ASSAY_PAYLOAD


def _bundle(
    outcome: str = "pass",
    url: str = "https://example.com",
    timestamp: str = "2026-04-16T10:00:00Z",
    error: str | None = None,
    screenshot_path: str | None = None,
) -> ArtifactBundle:
    return ArtifactBundle(
        outcome=outcome,
        url=url,
        suite="default",
        timestamp=timestamp,
        error=error,
        screenshot_path=screenshot_path,
        raw_result={},
    )


def _validate(packet: dict[str, object]) -> None:
    jsonschema.validate(instance=packet, schema=ASSAY_PAYLOAD)


def test_pass_packet_is_schema_valid() -> None:
    _validate(format_packet(_bundle(outcome="pass")))


def test_fail_packet_is_schema_valid() -> None:
    _validate(format_packet(_bundle(outcome="fail", error="navigation timeout")))


def test_inconclusive_packet_is_schema_valid() -> None:
    _validate(format_packet(_bundle(outcome="inconclusive")))


def test_with_screenshot_is_schema_valid() -> None:
    _validate(format_packet(_bundle(screenshot_path="/tmp/out/screenshot.png")))


def test_with_task_id_is_schema_valid() -> None:
    _validate(format_packet(_bundle(), task_id="TASK-0042"))


def test_standalone_task_id_none_is_schema_valid() -> None:
    packet = format_packet(_bundle())
    assert packet["task_id"] is None
    _validate(packet)


def test_empty_timestamp_fallback_is_schema_valid() -> None:
    _validate(format_packet(_bundle(timestamp="")))


def test_required_fields_all_present() -> None:
    packet = format_packet(_bundle())
    required = {"verification_id", "task_id", "issue_type", "severity", "outcome", "summary"}
    assert required.issubset(packet.keys())
    _validate(packet)


def test_invalid_outcome_fails_schema() -> None:
    packet = format_packet(_bundle())
    packet["outcome"] = "unknown"
    with pytest.raises(jsonschema.ValidationError):
        _validate(packet)


def test_missing_required_field_fails_schema() -> None:
    packet = format_packet(_bundle())
    del packet["summary"]
    with pytest.raises(jsonschema.ValidationError):
        _validate(packet)
