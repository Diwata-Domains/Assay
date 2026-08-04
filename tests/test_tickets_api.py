# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Tests: ticket surface REST API (/api/tickets*) — list rollup, detail, lifecycle actions.

Same Warden session auth as the rest of /api/*: unauthenticated requests are denied.
Actions map onto the CP-006 machine (propose-close / confirm-close / cancel via
`advance_ticket`) plus the founder-ruled 1:1 reopen (`reopen_ticket`).
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from grain_contracts.verification import State
from PIL import Image

from assay._vendor.warden import WardenConfig, issue_token
from assay.auth.admin import hash_password
from assay.ingest.app import app as ingest_app
from assay.store.db import (
    init_db,
    insert_packet,
    insert_ticket,
    set_source_ticket_id,
)

_SECRET = "x" * 32
_EMAIL = "admin@test.com"
_URL = "https://example.com/page"


def _png_bytes(color: tuple[int, int, int] = (10, 20, 30)) -> bytes:
    img = Image.new("RGB", (10, 10), color)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(tmp_path / "store.db")
    init_db(tmp_path / "store.db")
    client = TestClient(ingest_app, follow_redirects=False)
    client.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return client


def _unauth_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    ingest_app.state.store_db = str(tmp_path / "store.db")
    return TestClient(ingest_app, follow_redirects=False)


def _seed_ticket_with_packet(tmp_path: Path, state: State = State.IN_PROGRESS) -> tuple[str, str]:
    """Seed one ticket in `state` owning one fail packet with a screenshot + diff."""
    db = tmp_path / "store.db"
    init_db(db)
    ticket_id = insert_ticket(
        title="Login page renders blank",
        severity="error",
        priority="high",
        state=state,
        grain_task_id="TASK-0042",
        db_path=db,
    )
    png = tmp_path / "VERIFY-0001-001.png"
    png.write_bytes(_png_bytes())
    diff_png = tmp_path / "VERIFY-0001-001_diff.png"
    diff_png.write_bytes(_png_bytes((255, 0, 0)))
    packet: dict[str, object] = {
        "verification_id": "VERIFY-0001-001",
        "task_id": "TASK-0042",
        "issue_type": "visual_regression",
        "severity": "error",
        "outcome": "fail",
        "summary": "login page blank vs baseline",
        "url": _URL,
        "artifact_refs": [str(png), str(diff_png)],
        "followup_candidates": [],
        "verified_at": "2026-07-01T10:00:00Z",
        "diff_result": {"diff_pct": 42.0, "diff_image_path": str(diff_png)},
        "kind": "verification",
    }
    insert_packet(packet, db)
    set_source_ticket_id("VERIFY-0001-001", ticket_id, db)
    return ticket_id, "VERIFY-0001-001"


# --------------------------------------------------------------------------- auth


def test_api_tickets_requires_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _unauth_client(tmp_path, monkeypatch)
    assert client.get("/api/tickets").status_code in (303, 401)


def test_api_ticket_action_requires_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _unauth_client(tmp_path, monkeypatch)
    r = client.post("/api/tickets/ASSAY-1/action", json={"action": "confirm-close"})
    assert r.status_code in (303, 401)


# --------------------------------------------------------------------------- list


def test_list_tickets_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    r = client.get("/api/tickets")
    assert r.status_code == 200
    assert r.json() == {"tickets": [], "total": 0}


def test_list_tickets_includes_evidence_rollup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _setup(tmp_path, monkeypatch)
    ticket_id, vid = _seed_ticket_with_packet(tmp_path)
    r = client.get("/api/tickets")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    (ticket,) = body["tickets"]
    assert ticket["id"] == ticket_id
    assert ticket["title"] == "Login page renders blank"
    assert ticket["state"] == "in_progress"
    assert ticket["grain_task_id"] == "TASK-0042"
    ev = ticket["evidence"]
    assert ev["packet_count"] == 1
    assert ev["latest_verification_id"] == vid
    assert ev["latest_outcome"] == "fail"
    assert ev["latest_kind"] == "verification"
    assert ev["has_screenshot"] is True
    assert ev["has_diff"] is True


def test_list_tickets_without_packets_has_empty_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _setup(tmp_path, monkeypatch)
    db = tmp_path / "store.db"
    init_db(db)
    insert_ticket(title="Bare finding", severity="info", db_path=db)
    (ticket,) = client.get("/api/tickets").json()["tickets"]
    assert ticket["evidence"] == {
        "packet_count": 0,
        "latest_verification_id": None,
        "latest_outcome": None,
        "latest_verified_at": None,
        "latest_kind": None,
        "has_screenshot": False,
        "has_diff": False,
    }


# --------------------------------------------------------------------------- detail


def test_get_ticket_detail_with_packet_timeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _setup(tmp_path, monkeypatch)
    ticket_id, vid = _seed_ticket_with_packet(tmp_path)
    r = client.get(f"/api/tickets/{ticket_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == ticket_id
    assert body["evidence"]["latest_verification_id"] == vid
    (packet,) = body["packets"]
    assert packet["verification_id"] == vid
    assert packet["outcome"] == "fail"
    assert packet["has_diff"] is True


def test_get_ticket_unknown_404(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    assert client.get("/api/tickets/ASSAY-999").status_code == 404


# --------------------------------------------------------------------------- actions


def test_propose_close_moves_in_progress_to_in_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _setup(tmp_path, monkeypatch)
    ticket_id, _ = _seed_ticket_with_packet(tmp_path, state=State.IN_PROGRESS)
    r = client.post(f"/api/tickets/{ticket_id}/action", json={"action": "propose-close"})
    assert r.status_code == 200
    assert r.json() == {"id": ticket_id, "state": "in_review"}


def test_confirm_close_moves_in_review_to_done(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _setup(tmp_path, monkeypatch)
    ticket_id, _ = _seed_ticket_with_packet(tmp_path, state=State.IN_REVIEW)
    r = client.post(f"/api/tickets/{ticket_id}/action", json={"action": "confirm-close"})
    assert r.status_code == 200
    assert r.json() == {"id": ticket_id, "state": "done"}


def test_reopen_done_ticket_returns_to_in_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _setup(tmp_path, monkeypatch)
    ticket_id, _ = _seed_ticket_with_packet(tmp_path, state=State.DONE)
    r = client.post(f"/api/tickets/{ticket_id}/action", json={"action": "reopen"})
    assert r.status_code == 200
    assert r.json() == {"id": ticket_id, "state": "in_progress"}


def test_reopen_in_review_ticket_returns_to_in_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _setup(tmp_path, monkeypatch)
    ticket_id, _ = _seed_ticket_with_packet(tmp_path, state=State.IN_REVIEW)
    r = client.post(f"/api/tickets/{ticket_id}/action", json={"action": "reopen"})
    assert r.status_code == 200
    assert r.json() == {"id": ticket_id, "state": "in_progress"}


def test_reopen_triage_ticket_is_illegal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    ticket_id, _ = _seed_ticket_with_packet(tmp_path, state=State.TRIAGE)
    r = client.post(f"/api/tickets/{ticket_id}/action", json={"action": "reopen"})
    assert r.status_code == 400


def test_propose_close_from_triage_is_illegal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _setup(tmp_path, monkeypatch)
    ticket_id, _ = _seed_ticket_with_packet(tmp_path, state=State.TRIAGE)
    r = client.post(f"/api/tickets/{ticket_id}/action", json={"action": "propose-close"})
    assert r.status_code == 400


def test_cancel_triage_ticket(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    ticket_id, _ = _seed_ticket_with_packet(tmp_path, state=State.TRIAGE)
    r = client.post(f"/api/tickets/{ticket_id}/action", json={"action": "cancel"})
    assert r.status_code == 200
    assert r.json() == {"id": ticket_id, "state": "canceled"}


def test_unknown_action_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    ticket_id, _ = _seed_ticket_with_packet(tmp_path)
    r = client.post(f"/api/tickets/{ticket_id}/action", json={"action": "close"})
    assert r.status_code == 422


def test_action_on_unknown_ticket_404(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup(tmp_path, monkeypatch)
    r = client.post("/api/tickets/ASSAY-999/action", json={"action": "confirm-close"})
    assert r.status_code == 404
