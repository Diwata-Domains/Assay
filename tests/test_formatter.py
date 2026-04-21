"""Unit tests for the Grain Sentinel payload formatter."""

from __future__ import annotations

import re

from assay.formatter.formatter import format_packet
from assay.runner.artifacts import ArtifactBundle

_UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def _bundle(
    outcome: str = "pass",
    url: str = "https://example.com",
    suite: str = "default",
    timestamp: str = "2026-04-16T10:00:00Z",
    error: str | None = None,
    screenshot_path: str | None = None,
) -> ArtifactBundle:
    return ArtifactBundle(
        outcome=outcome,
        url=url,
        suite=suite,
        timestamp=timestamp,
        error=error,
        screenshot_path=screenshot_path,
        raw_result={},
    )


def test_verification_id_is_uuid4() -> None:
    packet = format_packet(_bundle())
    vid = str(packet["verification_id"])
    assert _UUID4_RE.match(vid), f"not a UUID4: {vid}"


def test_verification_id_unique_each_call() -> None:
    p1 = format_packet(_bundle())
    p2 = format_packet(_bundle())
    assert p1["verification_id"] != p2["verification_id"]


def test_task_id_defaults_none() -> None:
    packet = format_packet(_bundle())
    assert packet["task_id"] is None


def test_task_id_passed_through() -> None:
    packet = format_packet(_bundle(), task_id="TASK-0042")
    assert packet["task_id"] == "TASK-0042"


def test_pass_outcome_fields() -> None:
    packet = format_packet(_bundle(outcome="pass"))
    assert packet["outcome"] == "pass"
    assert packet["severity"] == "info"
    assert packet["issue_type"] == "test_failure"
    assert "pass" in str(packet["summary"])


def test_fail_outcome_fields() -> None:
    packet = format_packet(_bundle(outcome="fail", error="navigation timeout"))
    assert packet["outcome"] == "fail"
    assert packet["severity"] == "error"
    assert packet["issue_type"] == "test_failure"
    assert "navigation timeout" in str(packet["summary"])


def test_inconclusive_outcome_fields() -> None:
    packet = format_packet(_bundle(outcome="inconclusive"))
    assert packet["outcome"] == "inconclusive"
    assert packet["severity"] == "warning"
    assert packet["issue_type"] == "test_failure"


def test_screenshot_in_artifact_refs() -> None:
    packet = format_packet(_bundle(screenshot_path="/tmp/out/screenshot.png"))
    assert packet["artifact_refs"] == ["/tmp/out/screenshot.png"]


def test_no_screenshot_gives_empty_artifact_refs() -> None:
    packet = format_packet(_bundle(screenshot_path=None))
    assert packet["artifact_refs"] == []


def test_verified_at_uses_bundle_timestamp() -> None:
    packet = format_packet(_bundle(timestamp="2026-04-16T10:00:00Z"))
    assert packet["verified_at"] == "2026-04-16T10:00:00Z"


def test_verified_at_falls_back_to_current_time_when_empty() -> None:
    packet = format_packet(_bundle(timestamp=""))
    vat = str(packet["verified_at"])
    assert vat.endswith("Z")
    assert "T" in vat


def test_followup_candidates_empty() -> None:
    packet = format_packet(_bundle())
    assert packet["followup_candidates"] == []


def test_required_fields_present() -> None:
    packet = format_packet(_bundle())
    required = {"verification_id", "task_id", "issue_type", "severity", "outcome", "summary"}
    assert required.issubset(packet.keys())


# ---------------------------------------------------------------------------
# format_sdk_packet tests
# ---------------------------------------------------------------------------


def _sdk_payload() -> object:
    import base64

    from assay.ingest.app import IngestPayload

    return IngestPayload(
        captured_at="2026-04-18T10:00:00Z",
        url="https://example.com/page",
        viewport={"width": 1280, "height": 800},  # type: ignore[arg-type]
        user_agent="Mozilla/5.0",
        screenshot=base64.b64encode(b"fake").decode(),
    )


def test_format_sdk_packet_required_fields() -> None:
    from assay.formatter.formatter import format_sdk_packet

    packet = format_sdk_packet(_sdk_payload())  # type: ignore[arg-type]
    required = {"verification_id", "task_id", "issue_type", "severity", "outcome", "summary"}
    assert required.issubset(packet.keys())


def test_format_sdk_packet_issue_type() -> None:
    from assay.formatter.formatter import format_sdk_packet

    packet = format_sdk_packet(_sdk_payload())  # type: ignore[arg-type]
    assert packet["issue_type"] == "screenshot_evidence"


def test_format_sdk_packet_severity_info() -> None:
    from assay.formatter.formatter import format_sdk_packet

    packet = format_sdk_packet(_sdk_payload())  # type: ignore[arg-type]
    assert packet["severity"] == "info"


def test_format_sdk_packet_outcome_inconclusive() -> None:
    from assay.formatter.formatter import format_sdk_packet

    packet = format_sdk_packet(_sdk_payload())  # type: ignore[arg-type]
    assert packet["outcome"] == "inconclusive"


def test_format_sdk_packet_task_id_null() -> None:
    from assay.formatter.formatter import format_sdk_packet

    packet = format_sdk_packet(_sdk_payload())  # type: ignore[arg-type]
    assert packet["task_id"] is None


def test_format_sdk_packet_verified_at_from_payload() -> None:
    from assay.formatter.formatter import format_sdk_packet

    packet = format_sdk_packet(_sdk_payload())  # type: ignore[arg-type]
    assert packet["verified_at"] == "2026-04-18T10:00:00Z"


def test_format_sdk_packet_summary_contains_url() -> None:
    from assay.formatter.formatter import format_sdk_packet

    packet = format_sdk_packet(_sdk_payload())  # type: ignore[arg-type]
    assert "example.com" in str(packet["summary"])
