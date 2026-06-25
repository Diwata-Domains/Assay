"""Tests for the code-review verdict contract (Phase 30, P30-T02).

Covers the verdict -> outcome -> grain-review mapping, the CodeReviewResult / CodeReviewFinding
domain types (validation + round-trip), and that format_review_packet emits a packet that is
valid against the FROZEN assay_payload.schema.json (issue_type reuses bug_finding until CP-005).
"""

from __future__ import annotations

import re

import jsonschema
import pytest

from assay.review import (
    CodeReviewFinding,
    CodeReviewResult,
    CodeReviewVerdict,
    GrainReviewVerdict,
    PacketOutcome,
    format_review_packet,
    grain_review_for_outcome,
    outcome_for_verdict,
)
from assay.review.verdict import grain_review_for_verdict
from assay.schemas import ASSAY_PAYLOAD

_UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def _result(verdict: CodeReviewVerdict = CodeReviewVerdict.PASS) -> CodeReviewResult:
    return CodeReviewResult(
        verdict=verdict,
        summary=f"code review: {verdict.value}",
        findings=[CodeReviewFinding(file="src/x.py", line=10, severity="error", message="bug")],
        reviewers=["proposer", "critic", "judge"],
        confidence=0.8,
    )


# --- verdict -> outcome ---


@pytest.mark.parametrize(
    ("verdict", "outcome"),
    [
        (CodeReviewVerdict.PASS, PacketOutcome.PASS),
        (CodeReviewVerdict.FAIL, PacketOutcome.FAIL),
        (CodeReviewVerdict.INCONCLUSIVE, PacketOutcome.INCONCLUSIVE),
    ],
)
def test_outcome_for_verdict(verdict: CodeReviewVerdict, outcome: PacketOutcome) -> None:
    assert outcome_for_verdict(verdict) is outcome


def test_outcome_for_verdict_accepts_str() -> None:
    assert outcome_for_verdict("fail") is PacketOutcome.FAIL


# --- outcome -> grain review verdict ---


@pytest.mark.parametrize(
    ("outcome", "review"),
    [
        (PacketOutcome.PASS, GrainReviewVerdict.APPROVED),
        (PacketOutcome.FAIL, GrainReviewVerdict.NEEDS_FIX),
        (PacketOutcome.INCONCLUSIVE, GrainReviewVerdict.NEEDS_HUMAN),
    ],
)
def test_grain_review_for_outcome(outcome: PacketOutcome, review: GrainReviewVerdict) -> None:
    assert grain_review_for_outcome(outcome) is review


def test_grain_review_for_outcome_accepts_str() -> None:
    assert grain_review_for_outcome("pass") is GrainReviewVerdict.APPROVED


@pytest.mark.parametrize(
    ("verdict", "review"),
    [
        (CodeReviewVerdict.PASS, GrainReviewVerdict.APPROVED),
        (CodeReviewVerdict.FAIL, GrainReviewVerdict.NEEDS_FIX),
        (CodeReviewVerdict.INCONCLUSIVE, GrainReviewVerdict.NEEDS_HUMAN),
    ],
)
def test_grain_review_for_verdict_composes(
    verdict: CodeReviewVerdict, review: GrainReviewVerdict
) -> None:
    assert grain_review_for_verdict(verdict) is review


def test_verdict_values_match_outcome_enum() -> None:
    assert {v.value for v in CodeReviewVerdict} == {o.value for o in PacketOutcome}


def test_grain_review_string_values() -> None:
    assert GrainReviewVerdict.APPROVED.value == "approved"
    assert GrainReviewVerdict.NEEDS_FIX.value == "needs_fix"
    assert GrainReviewVerdict.NEEDS_HUMAN.value == "needs_human"


# --- result properties ---


def test_result_outcome_and_grain_review_pass() -> None:
    r = CodeReviewResult(verdict=CodeReviewVerdict.PASS, summary="ok")
    assert r.outcome is PacketOutcome.PASS
    assert r.grain_review is GrainReviewVerdict.APPROVED


def test_result_outcome_and_grain_review_fail() -> None:
    r = _result(CodeReviewVerdict.FAIL)
    assert r.outcome is PacketOutcome.FAIL
    assert r.grain_review is GrainReviewVerdict.NEEDS_FIX


def test_result_severity_is_highest_finding() -> None:
    r = CodeReviewResult(
        verdict=CodeReviewVerdict.FAIL,
        summary="s",
        findings=[
            CodeReviewFinding(file="a", severity="info", message="m"),
            CodeReviewFinding(file="b", severity="critical", message="m"),
            CodeReviewFinding(file="c", severity="warning", message="m"),
        ],
    )
    assert r.severity == "critical"


def test_result_severity_defaults_to_verdict_when_no_findings() -> None:
    assert CodeReviewResult(verdict=CodeReviewVerdict.PASS, summary="s").severity == "info"
    assert CodeReviewResult(verdict=CodeReviewVerdict.FAIL, summary="s").severity == "error"
    assert (
        CodeReviewResult(verdict=CodeReviewVerdict.INCONCLUSIVE, summary="s").severity == "warning"
    )


def test_result_coerces_str_verdict() -> None:
    r = CodeReviewResult(verdict="pass", summary="s")  # type: ignore[arg-type]
    assert r.verdict is CodeReviewVerdict.PASS


def test_result_rejects_empty_summary() -> None:
    with pytest.raises(ValueError, match="summary"):
        CodeReviewResult(verdict=CodeReviewVerdict.PASS, summary="")


def test_result_rejects_bad_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        CodeReviewResult(verdict=CodeReviewVerdict.PASS, summary="s", confidence=1.5)


# --- finding validation ---


def test_finding_rejects_empty_file() -> None:
    with pytest.raises(ValueError, match="file"):
        CodeReviewFinding(file="", severity="error", message="m")


def test_finding_rejects_empty_message() -> None:
    with pytest.raises(ValueError, match="message"):
        CodeReviewFinding(file="a", severity="error", message="")


def test_finding_rejects_bad_severity() -> None:
    with pytest.raises(ValueError, match="severity"):
        CodeReviewFinding(file="a", severity="fatal", message="m")


def test_finding_allows_none_line() -> None:
    f = CodeReviewFinding(file="a", severity="info", message="m", line=None)
    assert f.line is None


# --- round-trip ---


def test_result_round_trip() -> None:
    r = _result(CodeReviewVerdict.FAIL)
    restored = CodeReviewResult.from_dict(r.to_dict())
    assert restored == r


def test_finding_round_trip() -> None:
    f = CodeReviewFinding(file="src/y.py", line=3, severity="warning", message="hmm")
    assert CodeReviewFinding.from_dict(f.to_dict()) == f


def test_result_round_trip_empty_findings() -> None:
    r = CodeReviewResult(verdict=CodeReviewVerdict.INCONCLUSIVE, summary="unsure")
    restored = CodeReviewResult.from_dict(r.to_dict())
    assert restored == r


def test_review_block_shape() -> None:
    block = _result(CodeReviewVerdict.FAIL).review_block()
    assert block["verdict"] == "fail"
    assert block["reviewers"] == ["proposer", "critic", "judge"]
    assert block["confidence"] == 0.8
    assert isinstance(block["findings"], list)
    assert block["findings"][0]["file"] == "src/x.py"  # type: ignore[index]


# --- packet formatting against the frozen schema ---


def _validate(packet: dict[str, object]) -> None:
    jsonschema.validate(instance=packet, schema=ASSAY_PAYLOAD)


def test_packet_is_schema_valid_pass() -> None:
    _validate(format_review_packet(_result(CodeReviewVerdict.PASS)))


def test_packet_is_schema_valid_fail() -> None:
    _validate(format_review_packet(_result(CodeReviewVerdict.FAIL)))


def test_packet_is_schema_valid_inconclusive() -> None:
    _validate(format_review_packet(_result(CodeReviewVerdict.INCONCLUSIVE)))


def test_packet_issue_type_is_bug_finding_until_cp_lands() -> None:
    packet = format_review_packet(_result())
    assert packet["issue_type"] == "bug_finding"


def test_packet_has_no_review_block_until_cp_lands() -> None:
    packet = format_review_packet(_result())
    assert "review" not in packet


def test_packet_outcome_tracks_verdict() -> None:
    assert format_review_packet(_result(CodeReviewVerdict.PASS))["outcome"] == "pass"
    assert format_review_packet(_result(CodeReviewVerdict.FAIL))["outcome"] == "fail"
    assert (
        format_review_packet(_result(CodeReviewVerdict.INCONCLUSIVE))["outcome"] == "inconclusive"
    )


def test_packet_severity_tracks_findings() -> None:
    r = CodeReviewResult(
        verdict=CodeReviewVerdict.FAIL,
        summary="s",
        findings=[CodeReviewFinding(file="a", severity="critical", message="m")],
    )
    assert format_review_packet(r)["severity"] == "critical"


def test_packet_verification_id_defaults_to_uuid4() -> None:
    packet = format_review_packet(_result())
    assert _UUID4_RE.match(str(packet["verification_id"]))


def test_packet_verification_id_passed_through() -> None:
    packet = format_review_packet(_result(), verification_id="VERIFY-0077-001")
    assert packet["verification_id"] == "VERIFY-0077-001"


def test_packet_task_id_passed_through() -> None:
    packet = format_review_packet(_result(), task_id="TASK-0077")
    assert packet["task_id"] == "TASK-0077"


def test_packet_task_id_defaults_none() -> None:
    assert format_review_packet(_result())["task_id"] is None


def test_packet_transcript_refs_become_artifacts() -> None:
    r = CodeReviewResult(
        verdict=CodeReviewVerdict.PASS,
        summary="s",
        transcript_refs=["/out/transcript.json"],
    )
    packet = format_review_packet(r, artifact_refs=["/out/findings.json"])
    assert packet["artifact_refs"] == ["/out/findings.json", "/out/transcript.json"]


def test_packet_verified_at_passed_through() -> None:
    packet = format_review_packet(_result(), verified_at="2026-06-25T10:00:00Z")
    assert packet["verified_at"] == "2026-06-25T10:00:00Z"


def test_packet_verified_at_defaults_to_now() -> None:
    vat = str(format_review_packet(_result())["verified_at"])
    assert vat.endswith("Z") and "T" in vat
