# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Dashboard REST API — session-authenticated JSON + image endpoints.

These routes back the single-page dashboard app (mounted at ``/dashboard``). They
share the existing Warden session login with the server-rendered HTML dashboard:
the ``WardenMiddleware`` protects every path not listed in ``public_paths`` /
``public_prefixes``, so ``/api/*`` is session-gated automatically — it must NOT be
added to those public lists.

Everything here delegates to ``assay.store.db`` (paging + filtering happen in SQL,
never in memory) and to the same ``set_baseline`` / ``set_review_status`` store
logic the HTML dashboard's review buttons use.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from assay.store.db import (
    StoreError,
    count_packets,
    get_baseline_for_url,
    get_packet,
    list_baselines,
    list_packets_page,
    set_baseline,
    set_review_status,
)

router = APIRouter(prefix="/api")


def _db_path(request: Request) -> Path:
    return Path(request.app.state.store_db).expanduser()


def _candidate_png(packet: dict[str, object]) -> Optional[Path]:
    """The {vid}.png screenshot for a packet (a .png ref that is not the diff image)."""
    refs = packet.get("artifact_refs", [])
    ref_list = refs if isinstance(refs, list) else []
    for ref in ref_list:
        p = Path(str(ref))
        if p.suffix == ".png" and "_diff" not in p.stem:
            return p
    return None


def _diff_png(packet: dict[str, object]) -> Optional[Path]:
    diff = packet.get("diff_result")
    if not isinstance(diff, dict):
        return None
    path = str(diff.get("diff_image_path", ""))
    return Path(path) if path else None


def _summarize(packet: dict[str, object], baseline_vids: set[str]) -> dict[str, object]:
    vid = str(packet.get("verification_id", ""))
    diff = packet.get("diff_result")
    has_diff = isinstance(diff, dict)
    diff_pct: Optional[float] = None
    if isinstance(diff, dict) and diff.get("diff_pct") is not None:
        diff_pct = float(diff["diff_pct"])
    return {
        "verification_id": vid,
        "task_id": packet.get("task_id"),
        "outcome": str(packet.get("outcome", "")),
        "severity": str(packet.get("severity", "")),
        "review_status": packet.get("review_status"),
        "url": str(packet.get("url", "")),
        "verified_at": str(packet.get("verified_at", "")),
        "summary": str(packet.get("summary", "")),
        "is_baseline": vid in baseline_vids,
        "has_diff": has_diff,
        "diff_pct": diff_pct,
    }


@router.get("/packets")
async def api_list_packets(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    outcome: str = Query(default=""),
    task_id: str = Query(default=""),
) -> dict[str, object]:
    db = _db_path(request)
    outcome_filter = outcome.strip() or None
    task_filter = task_id.strip() or None
    try:
        total = count_packets(db, outcome=outcome_filter, task_id=task_filter)
        page = list_packets_page(
            db,
            outcome=outcome_filter,
            task_id=task_filter,
            limit=limit,
            offset=offset,
        )
        baseline_vids = set(list_baselines(db).values())
    except StoreError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {
        "packets": [_summarize(p, baseline_vids) for p in page],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _load_packet(request: Request, verification_id: str) -> dict[str, object]:
    try:
        packet = get_packet(verification_id, _db_path(request))
    except StoreError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if packet is None:
        raise HTTPException(status_code=404, detail=f"packet {verification_id} not found")
    return packet


@router.get("/packets/{verification_id}")
async def api_get_packet(request: Request, verification_id: str) -> dict[str, object]:
    db = _db_path(request)
    packet = _load_packet(request, verification_id)
    try:
        baseline_vids = set(list_baselines(db).values())
    except StoreError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    candidate = _candidate_png(packet)
    diff_path = _diff_png(packet)

    has_baseline = False
    url = str(packet.get("url", ""))
    if url:
        try:
            bl = get_baseline_for_url(url, db)
        except StoreError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        if bl is not None:
            bl_png = _candidate_png(bl)
            has_baseline = bl_png is not None and bl_png.exists()

    diff_result = packet.get("diff_result")
    return {
        "verification_id": str(packet.get("verification_id", "")),
        "task_id": packet.get("task_id"),
        "outcome": str(packet.get("outcome", "")),
        "severity": str(packet.get("severity", "")),
        "review_status": packet.get("review_status"),
        "url": url,
        "summary": str(packet.get("summary", "")),
        "verified_at": str(packet.get("verified_at", "")),
        "diff_result": diff_result if isinstance(diff_result, dict) else None,
        "has_candidate": candidate is not None and candidate.exists(),
        "has_baseline": has_baseline,
        "has_diff": diff_path is not None and diff_path.exists(),
        "is_baseline": str(packet.get("verification_id", "")) in baseline_vids,
    }


def _png_response(path: Optional[Path], filename: str) -> FileResponse:
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="image not found")
    return FileResponse(str(path), media_type="image/png", filename=filename)


@router.get("/packets/{verification_id}/candidate.png")
async def api_candidate_png(request: Request, verification_id: str) -> FileResponse:
    packet = _load_packet(request, verification_id)
    return _png_response(_candidate_png(packet), f"{verification_id}-candidate.png")


@router.get("/packets/{verification_id}/diff.png")
async def api_diff_png(request: Request, verification_id: str) -> FileResponse:
    packet = _load_packet(request, verification_id)
    return _png_response(_diff_png(packet), f"{verification_id}-diff.png")


@router.get("/packets/{verification_id}/baseline.png")
async def api_baseline_png(request: Request, verification_id: str) -> FileResponse:
    packet = _load_packet(request, verification_id)
    url = str(packet.get("url", ""))
    if not url:
        raise HTTPException(status_code=404, detail="image not found")
    try:
        baseline = get_baseline_for_url(url, _db_path(request))
    except StoreError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if baseline is None:
        raise HTTPException(status_code=404, detail="image not found")
    return _png_response(_candidate_png(baseline), f"{verification_id}-baseline.png")


class ReviewRequest(BaseModel):
    action: str

    @field_validator("action")
    @classmethod
    def known_action(cls, v: str) -> str:
        if v not in ("approve", "reject", "set-baseline"):
            raise ValueError("action must be one of: approve, reject, set-baseline")
        return v


@router.post("/packets/{verification_id}/review")
async def api_review(
    request: Request,
    verification_id: str,
    body: ReviewRequest,
) -> dict[str, object]:
    db = _db_path(request)
    if get_packet(verification_id, db) is None:
        raise HTTPException(status_code=404, detail=f"packet {verification_id} not found")
    try:
        if body.action == "approve":
            set_baseline(verification_id, db)
            set_review_status(verification_id, "approved", db)
            review_status: Optional[str] = "approved"
        elif body.action == "reject":
            set_review_status(verification_id, "rejected", db)
            review_status = "rejected"
        else:  # set-baseline
            set_baseline(verification_id, db)
            packet = get_packet(verification_id, db) or {}
            review_status = (
                str(packet.get("review_status")) if packet.get("review_status") is not None else None
            )
    except StoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"verification_id": verification_id, "review_status": review_status}
