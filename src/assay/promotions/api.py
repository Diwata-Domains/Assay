# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Promotions API — key-authed pull + ack for `triage_status="promoted"` packets.

This is the machine seam Grain pulls from: it lists packets an operator has
promoted out of the triage inbox (`/inbox`), and lets Grain acknowledge each one
once imported so it drops out of the pull list. Auth is the same `X-Assay-Key`
trust as `POST /ingest` — Grain has no Warden session to present, so this router
is added to the Warden `public_prefixes` allowlist in `ingest/app.py` and relies
entirely on `_require_api_key` for authentication.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from assay.ingest.api import _candidate_png
from assay.keys.require import _require_api_key
from assay.store.db import get_packet, list_packets_page, set_triage_status

router = APIRouter()


def _db_path(request: Request) -> Path:
    return Path(request.app.state.store_db).expanduser()


def _promotion_row(packet: dict[str, object]) -> dict[str, object]:
    png = _candidate_png(packet)
    return {
        "verification_id": str(packet.get("verification_id", "")),
        "url": str(packet.get("url", "")),
        "summary": str(packet.get("summary", "")),
        "severity": packet.get("severity"),
        "priority": packet.get("priority"),
        "user_comment": packet.get("user_comment"),
        "kind": packet.get("kind"),
        "screenshot_ref": str(png) if png is not None else None,
        "remediation": packet.get("remediation"),
    }


@router.get("/promotions")
async def list_promotions(
    request: Request,
    _key: str = Depends(_require_api_key),
) -> dict[str, object]:
    packets = list_packets_page(_db_path(request), triage_status="promoted")
    return {"promotions": [_promotion_row(p) for p in packets]}


@router.post("/promotions/{verification_id}/ack")
async def ack_promotion(
    verification_id: str,
    request: Request,
    _key: str = Depends(_require_api_key),
) -> dict[str, object]:
    db = _db_path(request)
    if get_packet(verification_id, db) is None:
        raise HTTPException(status_code=404, detail=f"packet {verification_id} not found")
    set_triage_status(verification_id, "imported", db)
    return {"verification_id": verification_id, "triage_status": "imported"}
