# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Formatter — converts ArtifactBundle or SDK IngestPayload to a Grain Sentinel payload dict."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from assay.runner.artifacts import ArtifactBundle

if TYPE_CHECKING:
    from assay.ingest.app import IngestPayload
    from assay.review.verdict import CodeReviewResult

_ISSUE_TYPE_MAP = {
    "pass": "test_failure",
    "fail": "test_failure",
    "inconclusive": "test_failure",
}

_SEVERITY_MAP = {
    "pass": "info",
    "fail": "error",
    "inconclusive": "warning",
}


def _summary(bundle: ArtifactBundle) -> str:
    """Build a human-readable one-line summary."""
    if bundle.outcome == "pass":
        return f"pass: {bundle.url}"
    if bundle.error:
        return f"{bundle.outcome}: {bundle.error}"
    return f"{bundle.outcome}: {bundle.url or 'unknown url'}"


def _verified_at(bundle: ArtifactBundle) -> str:
    """Return bundle timestamp or current UTC time in ISO 8601."""
    if bundle.timestamp:
        return bundle.timestamp
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_packet(
    bundle: ArtifactBundle,
    task_id: Optional[str] = None,  # noqa: UP007
    verification_id: Optional[str] = None,  # noqa: UP007
) -> dict[str, object]:
    """Convert an ArtifactBundle into a Grain Sentinel payload dict.

    Args:
        bundle: Populated ArtifactBundle from collect_artifacts().
        task_id: Grain TASK-#### ID being verified; None for standalone runs.
        verification_id: Grain-issued VERIFY-XXXX-NNN ID; generates UUID if None.

    Returns:
        Dict conforming to data_contracts.md §1 Grain Sentinel payload schema.
    """
    artifact_refs: list[str] = [bundle.screenshot_path] if bundle.screenshot_path else []

    # Collect all step screenshots into artifact_refs
    for step in bundle.steps:
        if step.screenshot_path and step.screenshot_path not in artifact_refs:
            artifact_refs.append(step.screenshot_path)

    packet: dict[str, object] = {
        "verification_id": verification_id if verification_id else str(uuid.uuid4()),
        "task_id": task_id,
        "issue_type": _ISSUE_TYPE_MAP.get(bundle.outcome, "test_failure"),
        "severity": _SEVERITY_MAP.get(bundle.outcome, "warning"),
        "outcome": bundle.outcome,
        "summary": _summary(bundle),
        "artifact_refs": artifact_refs,
        "followup_candidates": [],
        "verified_at": _verified_at(bundle),
    }

    if bundle.steps:
        packet["script_name"] = bundle.script_name
        packet["steps"] = [
            {
                "index": s.index,
                "type": s.type,
                "label": s.label,
                "outcome": s.outcome,
                "error": s.error,
                "screenshot": s.screenshot_path,
                **({
                    "expected": s.expected, "actual": s.actual
                } if s.expected is not None or s.actual is not None else {}),
            }
            for s in bundle.steps
        ]

    return packet


def format_review_packet(
    result: "CodeReviewResult",
    task_id: Optional[str] = None,  # noqa: UP007
    verification_id: Optional[str] = None,  # noqa: UP007
    artifact_refs: Optional[list[str]] = None,  # noqa: UP007
    verified_at: Optional[str] = None,  # noqa: UP007
) -> dict[str, object]:
    """Convert a CodeReviewResult into a Grain Sentinel payload dict (Phase 30 code-review mode).

    Mirrors the run -> format_packet -> submit packet path: the outcome comes from the verdict
    mapping (pass/fail/inconclusive), `verification_id` is passed through unchanged so the
    grain-issued VERIFY-XXXX-NNN survives, and the structured findings are folded into
    `summary` + `artifact_refs`. Since CP-005 landed the packet uses `issue_type=code_review`
    and surfaces the structured verdict in the optional `review` block.

    The verdict -> outcome contract and the schema-safe field shaping live in
    `assay.review.verdict.format_review_packet`; this is the formatter-package entry point the
    CLI and service call, keeping the code-review packet path next to format_packet.
    """
    from assay.review.verdict import format_review_packet as _format_review_packet

    return _format_review_packet(
        result,
        task_id=task_id,
        verification_id=verification_id,
        artifact_refs=artifact_refs,
        verified_at=verified_at,
    )


def format_sdk_packet(
    payload: "IngestPayload",
    verification_id: Optional[str] = None,  # noqa: UP007
) -> dict[str, object]:
    """Convert a browser SDK IngestPayload into a Grain Sentinel payload dict.

    Args:
        payload: Validated IngestPayload from the POST /ingest handler.
        verification_id: Grain-issued VERIFY-XXXX-NNN ID; generates UUID if None.

    Returns:
        Dict conforming to data_contracts.md §1 schema.
    """
    comment = payload.user_comment or ""
    summary = f"SDK capture: {payload.url}" + (f" — {comment}" if comment else "")

    return {
        "verification_id": verification_id if verification_id else str(uuid.uuid4()),
        "task_id": None,
        "issue_type": "screenshot_evidence",
        "severity": "info",
        "outcome": "inconclusive",
        "summary": summary,
        "artifact_refs": [],
        "followup_candidates": [],
        "verified_at": payload.captured_at,
    }
