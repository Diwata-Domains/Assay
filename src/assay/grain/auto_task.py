# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Auto-create Grain task packets on Assay failure events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from assay.config import AssayConfig


def _now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _output_dir(config: "AssayConfig") -> Path | None:
    repo = config.grain.repo.strip()
    output = config.grain.output_path.strip()
    if not repo or not output:
        return None
    return Path(repo) / output


def suggest_remediation(
    issue_type: str,
    check_type: str = "",
    assertion_name: str = "",
    target: str = "",
) -> str:
    if issue_type == "visual_regression":
        return (
            f"Review recent changes affecting {target}; "
            "compare baseline vs current screenshot in Assay dashboard"
        )
    if assertion_name in ("expect_header", "expect_absent", "expect_value") or check_type == "header":
        return f"Add the expected header to the server response for {target}"
    if check_type == "auth":
        if assertion_name == "unauthenticated_rejection":
            return f"Verify the auth middleware is enforcing authentication on {target}"
        return "Ensure the API key is valid and the endpoint is accessible to authenticated clients"
    if assertion_name == "status_code" or check_type == "http":
        return f"Ensure the endpoint returns the expected status code; check service health at {target}"
    if assertion_name in ("expect_text", "expect_not_text", "expect_visible", "expect_url"):
        return "Update the page content or navigation to match the expected state"
    return "Review the failure detail and fix the root cause"


def _is_duplicate(dest_dir: Path, match: dict[str, object]) -> bool:
    """Return True if any assay-*.json in dest_dir matches all fields in match."""
    import json as _json

    for f in dest_dir.glob("assay-*.json"):
        try:
            data: dict[str, object] = _json.loads(f.read_text())
        except Exception:
            continue
        if all(data.get(k) == v for k, v in match.items()):
            return True
    return False


def create_regression_task(
    url: str,
    diff_pct: float,
    changed_pixels: int,
    total_pixels: int,
    diff_image_path: str | None,
    config: "AssayConfig",
) -> str | None:
    """Write a Grain task packet for a visual regression. Returns the packet path or None."""
    if not config.grain.auto_create or not config.grain.repo:
        return None

    dest_dir = _output_dir(config)
    if dest_dir is None:
        return None

    from assay.formatter.writer import write_packet

    vid = str(uuid.uuid4())
    artifact_refs: list[str] = [diff_image_path] if diff_image_path else []
    packet: dict[str, object] = {
        "verification_id": vid,
        "task_id": None,
        "issue_type": "visual_regression",
        "severity": "error",
        "outcome": "fail",
        "summary": f"Visual regression: {url} — {diff_pct}% changed ({changed_pixels}/{total_pixels} px)",
        "artifact_refs": artifact_refs,
        "followup_candidates": [],
        "verified_at": _now(),
        "url": url,
        "diff_pct": diff_pct,
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "remediation": suggest_remediation("visual_regression", target=url),
    }

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        if _is_duplicate(dest_dir, {"issue_type": "visual_regression", "url": url}):
            return None
        return str(write_packet(packet, str(dest_dir)))
    except Exception as exc:
        import warnings
        warnings.warn(f"assay: failed to write regression task: {exc}", stacklevel=2)
        return None


def create_check_failure_task(
    check_id: str,
    check_type: str,
    target: str,
    failed_assertions: list[dict[str, object]],
    error: str | None,
    config: "AssayConfig",
) -> str | None:
    """Write a Grain task packet for a failing check. Returns the packet path or None."""
    if not config.grain.auto_create or not config.grain.repo:
        return None

    dest_dir = _output_dir(config)
    if dest_dir is None:
        return None

    from assay.formatter.writer import write_packet

    vid = str(uuid.uuid4())
    detail_lines = []
    for a in failed_assertions:
        detail_lines.append(
            f"  {a['name']}: expected={a['expected']!r} actual={a['actual']!r}"
        )
    detail = "\n".join(detail_lines) if detail_lines else (error or "unknown failure")
    first_assertion = str(failed_assertions[0]["name"]) if failed_assertions else ""

    packet: dict[str, object] = {
        "verification_id": vid,
        "task_id": None,
        "issue_type": "check_failure",
        "severity": "error",
        "outcome": "fail",
        "summary": f"Check failure: {check_id} ({check_type}) — {target}",
        "artifact_refs": [],
        "followup_candidates": [],
        "verified_at": _now(),
        "check_id": check_id,
        "check_type": check_type,
        "target": target,
        "detail": detail,
        "remediation": suggest_remediation(
            "check_failure", check_type=check_type, assertion_name=first_assertion, target=target
        ),
    }
    if error:
        packet["error"] = error

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        if _is_duplicate(dest_dir, {"issue_type": "check_failure", "check_id": check_id, "target": target}):
            return None
        return str(write_packet(packet, str(dest_dir)))
    except Exception as exc:
        import warnings
        warnings.warn(f"assay: failed to write check failure task: {exc}", stacklevel=2)
        return None
