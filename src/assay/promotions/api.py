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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from grain_contracts.verification import State
from pydantic import BaseModel

from assay.ingest.api import _candidate_png
from assay.keys.require import _require_api_key
from assay.store.db import (
    advance_ticket,
    get_packet,
    get_ticket,
    list_packets_page,
    set_ticket_grain_task_id,
    set_triage_status,
)

router = APIRouter()


class AckRequest(BaseModel):
    grain_task_id: Optional[str] = None  # noqa: UP007


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
    body: Optional[AckRequest] = None,  # noqa: UP007
    _key: str = Depends(_require_api_key),
) -> dict[str, object]:
    db = _db_path(request)
    packet = get_packet(verification_id, db)
    if packet is None:
        raise HTTPException(status_code=404, detail=f"packet {verification_id} not found")
    set_triage_status(verification_id, "imported", db)

    grain_task_id = body.grain_task_id if body is not None else None
    ticket_id = packet.get("source_ticket_id")
    if grain_task_id and ticket_id:
        set_ticket_grain_task_id(str(ticket_id), grain_task_id, db)
        ticket = get_ticket(str(ticket_id), db)
        # Advance `todo -> in_progress` only when the ticket is actually in `todo`.
        # A re-ack (ticket already left `todo`) is a no-op rather than an illegal
        # transition, so genuine StoreErrors (not-found, real illegal moves) are not
        # swallowed here.
        if ticket is not None and ticket.get("state") == State.TODO.value:
            advance_ticket(str(ticket_id), State.IN_PROGRESS, db)
    return {
        "verification_id": verification_id,
        "triage_status": "imported",
        "grain_task_id": grain_task_id,
        "ticket_id": ticket_id,
    }
