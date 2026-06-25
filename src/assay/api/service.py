# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Engine service layer — the single source of truth for agent-driven verification.

The CLI, the HTTP ingest server, and the MCP server all call into this module so the
verification loop behaves identically regardless of surface. Nothing here returns canned
data: ``run_verification`` drives the real runner and persists a real packet,
``get_report`` reads the real store, and the baseline functions mutate the real baselines
table.

The runner is injected as a callable so tests can drive the full loop without Docker or a
browser. Production code passes the default which calls the Docker / direct Playwright runner.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, Optional

from assay import telemetry as _telemetry
from assay.formatter.formatter import format_packet
from assay.formatter.writer import write_packet
from assay.runner import artifacts as _artifacts
from assay.runner import runner as _runner
from assay.runner.runner import RunResult
from assay.store import db as _store

RunnerFn = Callable[[str, str, str, bool], RunResult]


class ServiceError(Exception):
    """Raised when a verification or report request cannot be fulfilled."""


def _default_runner(target: str, suite: str, output_dir: str, no_docker: bool) -> RunResult:
    if no_docker:
        return _runner.run_direct(target, suite=suite, output_dir=output_dir)
    return _runner.run(target, suite=suite, output_dir=output_dir)


def run_verification(
    target: str,
    *,
    suite: str = "default",
    output_dir: str = "./assay-output",
    store_db: str,
    task_id: Optional[str] = None,
    verification_id: Optional[str] = None,
    no_docker: bool = False,
    runner_fn: Optional[RunnerFn] = None,
    compare: bool = True,
    threshold: float = 0.1,
) -> dict[str, object]:
    """Run a real verification: execute the runner, format + persist a packet, diff baseline.

    Returns a structured result dict (the report shape used everywhere):
    ``verification_id``, ``outcome``, ``packet_path``, ``url``, ``task_id``, ``summary``,
    ``artifact_refs``, ``diff`` (when a baseline exists), and ``regression`` (bool).
    """
    if not target:
        raise ServiceError("target is required")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    run = runner_fn if runner_fn is not None else _default_runner
    run_result = run(target, suite, output_dir, no_docker)
    try:
        bundle = _artifacts.collect_artifacts(run_result.output_dir, run_result)
    except _artifacts.ArtifactError as exc:
        raise ServiceError(f"failed to read run artifacts: {exc}") from exc

    packet = format_packet(bundle, task_id=task_id, verification_id=verification_id)
    packet["url"] = bundle.url or target
    vid = str(packet["verification_id"])

    candidate_png: Optional[Path] = None
    if bundle.screenshot_path:
        src = Path(bundle.screenshot_path)
        if src.exists():
            dest = out / f"{vid}.png"
            shutil.copy2(src, dest)
            packet["artifact_refs"] = [str(dest)]
            candidate_png = dest

    db_path = Path(store_db).expanduser()
    _store.init_db(db_path)

    diff_info: Optional[dict[str, object]] = None
    regression = False
    if compare and candidate_png is not None:
        diff_info, regression = _diff_against_baseline(
            url=str(packet["url"]),
            candidate_png=candidate_png,
            verification_id=vid,
            output_dir=output_dir,
            db_path=db_path,
            threshold=threshold,
        )
        if diff_info is not None:
            packet["diff_result"] = diff_info
            refs = packet.get("artifact_refs", [])
            ref_list = list(refs) if isinstance(refs, list) else []
            diff_img = diff_info.get("diff_image_path")
            if diff_img:
                packet["artifact_refs"] = ref_list + [diff_img]

    packet_path = write_packet(packet, output_dir)
    try:
        _store.insert_packet(packet, db_path)
    except _store.StoreError as exc:
        raise ServiceError(f"failed to persist packet: {exc}") from exc

    result: dict[str, object] = {
        "verification_id": vid,
        "outcome": bundle.outcome,
        "packet_path": str(packet_path),
        "url": str(packet["url"]),
        "task_id": task_id,
        "summary": str(packet.get("summary", "")),
        "artifact_refs": packet.get("artifact_refs", []),
        "regression": regression,
    }
    if bundle.error:
        result["error"] = bundle.error
    if diff_info is not None:
        result["diff"] = diff_info

    _emit_verification_completed(vid, str(packet["url"]), bundle)
    return result


def _check_counts(bundle: _artifacts.ArtifactBundle) -> tuple[int, int]:
    """Return (checks_total, checks_passed) for a verification.

    Script runs carry per-step results; a single-shot run is one logical check
    keyed off the overall outcome. Counts only — never any step content.
    """
    if bundle.steps:
        total = len(bundle.steps)
        passed = sum(1 for s in bundle.steps if s.outcome == "pass")
        return total, passed
    passed = 1 if bundle.outcome == "pass" else 0
    return 1, passed


def _emit_verification_completed(
    verification_id: str,
    target: str,
    bundle: _artifacts.ArtifactBundle,
) -> None:
    """Side-band telemetry hook — opt-in, fire-and-forget, never affects the result."""
    if not _telemetry.is_enabled():
        return
    checks_total, checks_passed = _check_counts(bundle)
    _telemetry.emit(
        _telemetry.make_verification_completed_event(
            verification_id,
            target,
            passed=bundle.outcome == "pass",
            checks_total=checks_total,
            checks_passed=checks_passed,
        )
    )


def _diff_against_baseline(
    *,
    url: str,
    candidate_png: Path,
    verification_id: str,
    output_dir: str,
    db_path: Path,
    threshold: float,
) -> tuple[Optional[dict[str, object]], bool]:
    from assay.diff.engine import DiffError
    from assay.diff.engine import diff_images as _diff

    baseline = _store.get_baseline_for_url(url, db_path)
    if baseline is None:
        return None, False
    refs = baseline.get("artifact_refs", [])
    ref_list = refs if isinstance(refs, list) else []
    baseline_png: Optional[Path] = None
    for ref in ref_list:
        bp = Path(str(ref))
        if bp.suffix == ".png" and "_diff" not in bp.stem and bp.exists():
            baseline_png = bp
            break
    if baseline_png is None:
        return None, False

    diff_path = Path(output_dir) / f"{verification_id}_diff.png"
    try:
        diff_result = _diff(baseline_png, candidate_png, diff_path)
    except DiffError:
        return None, False

    info: dict[str, object] = {
        "changed_pixels": diff_result.changed_pixels,
        "total_pixels": diff_result.total_pixels,
        "diff_pct": diff_result.diff_pct,
        "diff_image_path": diff_result.diff_image_path,
        "threshold": threshold,
    }
    return info, diff_result.diff_pct > threshold


def get_report(
    verification_id: str,
    *,
    store_db: str,
) -> Optional[dict[str, object]]:
    """Return the structured report for a verification_id from the store, or None."""
    db_path = Path(store_db).expanduser()
    packets = _store.list_packets(db_path)
    packet = next(
        (p for p in packets if str(p.get("verification_id", "")) == verification_id),
        None,
    )
    if packet is None:
        return None
    return _report_from_packet(packet, db_path)


def _report_from_packet(packet: dict[str, object], db_path: Path) -> dict[str, object]:
    url = str(packet.get("url", ""))
    baselines = _store.list_baselines(db_path)
    vid = str(packet.get("verification_id", ""))
    report: dict[str, object] = {
        "verification_id": vid,
        "task_id": packet.get("task_id"),
        "outcome": str(packet.get("outcome", "")),
        "severity": str(packet.get("severity", "")),
        "summary": str(packet.get("summary", "")),
        "url": url,
        "verified_at": str(packet.get("verified_at", "")),
        "artifact_refs": packet.get("artifact_refs", []),
        "review_status": packet.get("review_status"),
        "is_baseline": vid in set(baselines.values()),
    }
    diff = packet.get("diff_result")
    if isinstance(diff, dict):
        report["diff"] = diff
        threshold = diff.get("threshold", 0.1)
        try:
            report["regression"] = float(str(diff.get("diff_pct", 0))) > float(str(threshold))
        except (TypeError, ValueError):
            report["regression"] = False
    return report


def list_runs(
    *,
    store_db: str,
    task_id: Optional[str] = None,
    outcome: Optional[str] = None,
) -> list[dict[str, object]]:
    """Return run summaries from the store, optionally filtered by task_id / outcome."""
    db_path = Path(store_db).expanduser()
    packets = _store.list_packets(db_path, outcome=outcome, task_id=task_id)
    runs: list[dict[str, object]] = []
    for p in packets:
        refs = p.get("artifact_refs", [])
        ref_list = refs if isinstance(refs, list) else []
        runs.append(
            {
                "verification_id": str(p.get("verification_id", "")),
                "task_id": p.get("task_id"),
                "outcome": str(p.get("outcome", "")),
                "summary": str(p.get("summary", "")),
                "url": str(p.get("url", "")),
                "verified_at": str(p.get("verified_at", "")),
                "review_status": p.get("review_status"),
                "has_screenshot": any(str(r).endswith(".png") for r in ref_list),
            }
        )
    return runs


def list_baselines(*, store_db: str) -> list[dict[str, str]]:
    """Return [{url, verification_id}] for every set baseline."""
    db_path = Path(store_db).expanduser()
    mapping = _store.list_baselines(db_path)
    return [{"url": url, "verification_id": vid} for url, vid in mapping.items()]


def set_baseline(verification_id: str, *, store_db: str) -> dict[str, object]:
    """Make a packet the baseline for its URL. Returns {url, verification_id}."""
    db_path = Path(store_db).expanduser()
    try:
        url = _store.set_baseline(verification_id, db_path)
    except _store.StoreError as exc:
        raise ServiceError(str(exc)) from exc
    return {"url": url, "verification_id": verification_id}


def approve_baseline(verification_id: str, *, store_db: str) -> dict[str, object]:
    """Approve a packet: set it as baseline for its URL and mark review_status=approved."""
    db_path = Path(store_db).expanduser()
    try:
        url = _store.set_baseline(verification_id, db_path)
        _store.set_review_status(verification_id, "approved", db_path)
    except _store.StoreError as exc:
        raise ServiceError(str(exc)) from exc
    return {"url": url, "verification_id": verification_id, "review_status": "approved"}


def reject_baseline(verification_id: str, *, store_db: str) -> dict[str, object]:
    """Reject a packet: mark review_status=rejected without changing the baseline."""
    db_path = Path(store_db).expanduser()
    try:
        _store.set_review_status(verification_id, "rejected", db_path)
    except _store.StoreError as exc:
        raise ServiceError(str(exc)) from exc
    return {"verification_id": verification_id, "review_status": "rejected"}
