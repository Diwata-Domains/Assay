# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Code-review verdict contract.

Domain types for the adversarial code-review mode and the deterministic mapping from a
reviewer verdict to the Assay packet `outcome` and the Grain `review` verdict.

The mapping is the load-bearing contract for the Assay -> Grain bridge:

    verdict        outcome        grain review
    -----------    -----------    ------------
    pass           pass           approved
    fail           fail           needs_fix
    inconclusive   inconclusive   needs_human

`format_review_packet` emits a packet that is valid against the CURRENT frozen
`assay_payload.schema.json`: until CP-005 lands it reuses `issue_type = "bug_finding"` and
folds findings into `summary` + `artifact_refs` rather than emitting an unschema'd `review`
block or the not-yet-approved `code_review` issue_type.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class CodeReviewVerdict(str, Enum):
    """Verdict produced by the multi-agent code-review judge."""

    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class PacketOutcome(str, Enum):
    """Assay packet `outcome` enum (data_contracts.md §1)."""

    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class GrainReviewVerdict(str, Enum):
    """The `grain review` verdict a packet outcome resolves to on the Grain side."""

    APPROVED = "approved"
    NEEDS_FIX = "needs_fix"
    NEEDS_HUMAN = "needs_human"


_VERDICT_TO_OUTCOME: dict[CodeReviewVerdict, PacketOutcome] = {
    CodeReviewVerdict.PASS: PacketOutcome.PASS,
    CodeReviewVerdict.FAIL: PacketOutcome.FAIL,
    CodeReviewVerdict.INCONCLUSIVE: PacketOutcome.INCONCLUSIVE,
}

_OUTCOME_TO_GRAIN_REVIEW: dict[PacketOutcome, GrainReviewVerdict] = {
    PacketOutcome.PASS: GrainReviewVerdict.APPROVED,
    PacketOutcome.FAIL: GrainReviewVerdict.NEEDS_FIX,
    PacketOutcome.INCONCLUSIVE: GrainReviewVerdict.NEEDS_HUMAN,
}

# Until CP-005 is applied, code_review packets stay schema-valid by reusing this issue_type.
REVIEW_ISSUE_TYPE = "bug_finding"

_SEVERITY_VALUES = ("info", "warning", "error", "critical")

_VERDICT_TO_SEVERITY: dict[CodeReviewVerdict, str] = {
    CodeReviewVerdict.PASS: "info",
    CodeReviewVerdict.FAIL: "error",
    CodeReviewVerdict.INCONCLUSIVE: "warning",
}


def outcome_for_verdict(verdict: CodeReviewVerdict | str) -> PacketOutcome:
    """Map a reviewer verdict to the Assay packet `outcome`."""
    return _VERDICT_TO_OUTCOME[CodeReviewVerdict(verdict)]


def grain_review_for_outcome(outcome: PacketOutcome | str) -> GrainReviewVerdict:
    """Map a packet `outcome` to the Grain `review` verdict (approved/needs_fix/needs_human)."""
    return _OUTCOME_TO_GRAIN_REVIEW[PacketOutcome(outcome)]


def grain_review_for_verdict(verdict: CodeReviewVerdict | str) -> GrainReviewVerdict:
    """Convenience: verdict -> grain review, composing the two mappings."""
    return grain_review_for_outcome(outcome_for_verdict(verdict))


@dataclass(frozen=True)
class CodeReviewFinding:
    """A single structured finding from the code-review reviewers."""

    file: str
    severity: str
    message: str
    line: Optional[int] = None  # noqa: UP007  # 1-based; None for file-level findings

    def __post_init__(self) -> None:
        if not self.file:
            raise ValueError("finding.file must be non-empty")
        if not self.message:
            raise ValueError("finding.message must be non-empty")
        if self.severity not in _SEVERITY_VALUES:
            raise ValueError(
                f"finding.severity must be one of {_SEVERITY_VALUES}, got {self.severity!r}"
            )
        if self.line is not None and self.line < 0:
            raise ValueError("finding.line must be >= 0 or None")

    def to_dict(self) -> dict[str, object]:
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CodeReviewFinding:
        raw_line = data.get("line")
        line = int(raw_line) if isinstance(raw_line, int) else None
        return cls(
            file=str(data["file"]),
            severity=str(data["severity"]),
            message=str(data["message"]),
            line=line,
        )


@dataclass(frozen=True)
class CodeReviewResult:
    """Deterministic output of a code-review run: verdict + structured findings + provenance.

    This is the domain type the multi-agent runner (P30-T03) produces. The verdict drives the
    packet `outcome` and the Grain `review` verdict; the findings/reviewers/confidence become
    the `review` block once CP-005 lands (and are preserved as artifacts/summary until then).
    """

    verdict: CodeReviewVerdict
    summary: str
    findings: list[CodeReviewFinding] = field(default_factory=list)
    reviewers: list[str] = field(default_factory=list)
    confidence: float = 0.0
    transcript_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.verdict, CodeReviewVerdict):
            object.__setattr__(self, "verdict", CodeReviewVerdict(self.verdict))
        if not self.summary:
            raise ValueError("CodeReviewResult.summary must be non-empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("CodeReviewResult.confidence must be in [0.0, 1.0]")

    @property
    def outcome(self) -> PacketOutcome:
        return outcome_for_verdict(self.verdict)

    @property
    def grain_review(self) -> GrainReviewVerdict:
        return grain_review_for_outcome(self.outcome)

    @property
    def severity(self) -> str:
        """Packet-level severity: the highest finding severity, else verdict default."""
        if self.findings:
            return max(self.findings, key=lambda f: _SEVERITY_VALUES.index(f.severity)).severity
        return _VERDICT_TO_SEVERITY[self.verdict]

    def review_block(self) -> dict[str, object]:
        """The structured `review` block (surfaced on the wire once CP-005 is applied)."""
        return {
            "verdict": self.verdict.value,
            "findings": [f.to_dict() for f in self.findings],
            "reviewers": list(self.reviewers),
            "confidence": self.confidence,
        }

    def to_dict(self) -> dict[str, object]:
        """Round-trippable representation of the verdict result (not the wire packet)."""
        return {
            "verdict": self.verdict.value,
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
            "reviewers": list(self.reviewers),
            "confidence": self.confidence,
            "transcript_refs": list(self.transcript_refs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CodeReviewResult:
        raw_findings = data.get("findings", [])
        findings = [
            CodeReviewFinding.from_dict(f)
            for f in (raw_findings if isinstance(raw_findings, list) else [])
            if isinstance(f, dict)
        ]
        raw_reviewers = data.get("reviewers", [])
        reviewers = [str(r) for r in raw_reviewers] if isinstance(raw_reviewers, list) else []
        raw_refs = data.get("transcript_refs", [])
        transcript_refs = [str(r) for r in raw_refs] if isinstance(raw_refs, list) else []
        raw_conf = data.get("confidence", 0.0)
        confidence = float(raw_conf) if isinstance(raw_conf, (int, float)) else 0.0
        return cls(
            verdict=CodeReviewVerdict(str(data["verdict"])),
            summary=str(data["summary"]),
            findings=findings,
            reviewers=reviewers,
            confidence=confidence,
            transcript_refs=transcript_refs,
        )


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_review_packet(
    result: CodeReviewResult,
    task_id: Optional[str] = None,  # noqa: UP007
    verification_id: Optional[str] = None,  # noqa: UP007
    artifact_refs: Optional[list[str]] = None,  # noqa: UP007
    verified_at: Optional[str] = None,  # noqa: UP007
) -> dict[str, object]:
    """Convert a CodeReviewResult into an Assay payload dict valid against the FROZEN schema.

    Backward-compatible until CP-005 lands:
    - `issue_type` is `bug_finding` (not the not-yet-approved `code_review`).
    - No `review` block is emitted (the schema is additionalProperties:false). The structured
      findings are preserved via `summary` and `artifact_refs` (the runner writes findings +
      transcripts to disk and passes their paths here).
    """
    refs = list(artifact_refs) if artifact_refs else []
    for ref in result.transcript_refs:
        if ref not in refs:
            refs.append(ref)

    return {
        "verification_id": verification_id if verification_id else str(uuid.uuid4()),
        "task_id": task_id,
        "issue_type": REVIEW_ISSUE_TYPE,
        "severity": result.severity,
        "outcome": result.outcome.value,
        "summary": result.summary,
        "artifact_refs": refs,
        "followup_candidates": [],
        "verified_at": verified_at if verified_at else _now_iso(),
    }
