"""Formatter — converts ArtifactBundle or SDK IngestPayload to a Grain Sentinel payload dict."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from assay.runner.artifacts import ArtifactBundle

if TYPE_CHECKING:
    from assay.ingest.app import IngestPayload

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
) -> dict[str, object]:
    """Convert an ArtifactBundle into a Grain Sentinel payload dict.

    Args:
        bundle: Populated ArtifactBundle from collect_artifacts().
        task_id: Grain TASK-#### ID being verified; None for standalone runs.

    Returns:
        Dict conforming to data_contracts.md §1 Grain Sentinel payload schema.
    """
    artifact_refs: list[str] = [bundle.screenshot_path] if bundle.screenshot_path else []

    return {
        "verification_id": str(uuid.uuid4()),
        "task_id": task_id,
        "issue_type": _ISSUE_TYPE_MAP.get(bundle.outcome, "test_failure"),
        "severity": _SEVERITY_MAP.get(bundle.outcome, "warning"),
        "outcome": bundle.outcome,
        "summary": _summary(bundle),
        "artifact_refs": artifact_refs,
        "followup_candidates": [],
        "verified_at": _verified_at(bundle),
    }


def format_sdk_packet(payload: "IngestPayload") -> dict[str, object]:
    """Convert a browser SDK IngestPayload into a Grain Sentinel payload dict.

    Args:
        payload: Validated IngestPayload from the POST /ingest handler.

    Returns:
        Dict conforming to data_contracts.md §1 schema.
    """
    comment = payload.user_comment or ""
    summary = f"SDK capture: {payload.url}" + (f" — {comment}" if comment else "")

    return {
        "verification_id": str(uuid.uuid4()),
        "task_id": None,
        "issue_type": "screenshot_evidence",
        "severity": "info",
        "outcome": "inconclusive",
        "summary": summary,
        "artifact_refs": [],
        "followup_candidates": [],
        "verified_at": payload.captured_at,
    }
