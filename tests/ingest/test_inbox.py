# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Tests: GET /inbox triage list + POST /inbox/{vid}/triage promote/dismiss."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from assay._vendor.warden import WardenConfig, issue_token
from assay.auth.admin import hash_password
from assay.ingest.app import app
from assay.store.db import get_packet, init_db, insert_packet, set_triage_status

_SECRET = "x" * 32
_EMAIL = "admin@test.com"
_XSS = "<script>alert('x')</script>"


def _seed_packet(db: Path, vid: str = "vid-001", **overrides: object) -> None:
    packet: dict[str, object] = {
        "verification_id": vid,
        "task_id": None,
        "issue_type": "screenshot_evidence",
        "severity": "info",
        "outcome": "fail",
        "summary": "layout broke on checkout",
        "url": "https://example.com/checkout",
        "user_comment": "the button disappeared",
        "artifact_refs": [],
        "followup_candidates": [],
        "verified_at": "2026-07-07T00:00:00Z",
        "raw": "{}",
    }
    packet.update(overrides)
    insert_packet(packet, db)
    set_triage_status(vid, "new", db)


@pytest.fixture
def triage_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[TestClient, str, Path]:
    """Session-authenticated TestClient with one "new" packet seeded in the inbox."""
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    db = tmp_path / "store.db"
    init_db(db)
    vid = "vid-001"
    _seed_packet(db, vid)
    app.state.key_store = str(tmp_path / "keys.json")
    app.state.output_dir = str(tmp_path)
    app.state.store_db = str(db)
    client = TestClient(app, follow_redirects=False)
    client.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return client, vid, db


# --- route tests from the brief ---


def test_promote_sets_status_and_fields(
    triage_client: tuple[TestClient, str, Path],
) -> None:
    client, vid, db = triage_client
    r = client.post(
        f"/inbox/{vid}/triage",
        data={"action": "promote", "severity": "error", "priority": "high"},
    )
    assert r.status_code in (200, 303)
    p = get_packet(vid, db)
    assert p is not None
    assert p["triage_status"] == "promoted"
    assert p["severity"] == "error"
    assert p["priority"] == "high"


def test_dismiss_sets_status(triage_client: tuple[TestClient, str, Path]) -> None:
    client, vid, db = triage_client
    client.post(f"/inbox/{vid}/triage", data={"action": "dismiss"})
    p = get_packet(vid, db)
    assert p is not None
    assert p["triage_status"] == "dismissed"


# --- GET /inbox ---


def test_inbox_requires_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    app.state.store_db = str(tmp_path / "store.db")
    client = TestClient(app, follow_redirects=False)
    r = client.get("/inbox")
    assert r.status_code == 401


def test_inbox_lists_new_packets(triage_client: tuple[TestClient, str, Path]) -> None:
    client, vid, _db = triage_client
    r = client.get("/inbox")
    assert r.status_code == 200
    assert vid in r.text
    assert "checkout" in r.text


def test_inbox_excludes_non_new_packets(
    triage_client: tuple[TestClient, str, Path],
) -> None:
    client, vid, db = triage_client
    set_triage_status(vid, "promoted", db)
    r = client.get("/inbox")
    assert r.status_code == 200
    assert vid not in r.text


def test_inbox_escapes_packet_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    db = tmp_path / "store.db"
    init_db(db)
    _seed_packet(
        db,
        vid="vid-xss",
        summary=_XSS,
        user_comment=_XSS,
        url=f"https://evil.example/{_XSS}",
    )
    app.state.key_store = str(tmp_path / "keys.json")
    app.state.output_dir = str(tmp_path)
    app.state.store_db = str(db)
    client = TestClient(app, follow_redirects=False)
    client.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))

    r = client.get("/inbox")
    assert r.status_code == 200
    assert _XSS not in r.text
    assert "&lt;script&gt;" in r.text


# --- POST /inbox/{vid}/triage error paths ---


def test_triage_missing_packet_returns_404(
    triage_client: tuple[TestClient, str, Path],
) -> None:
    client, _vid, _db = triage_client
    r = client.post("/inbox/does-not-exist/triage", data={"action": "promote"})
    assert r.status_code == 404


def test_triage_invalid_action_returns_400(
    triage_client: tuple[TestClient, str, Path],
) -> None:
    client, vid, _db = triage_client
    r = client.post(f"/inbox/{vid}/triage", data={"action": "bogus"})
    assert r.status_code == 400


def test_triage_redirects_to_inbox(triage_client: tuple[TestClient, str, Path]) -> None:
    client, vid, _db = triage_client
    r = client.post(f"/inbox/{vid}/triage", data={"action": "dismiss"})
    assert r.status_code == 303
    assert r.headers["location"] == "/inbox"


def test_triage_without_severity_or_priority_leaves_them_unset(
    triage_client: tuple[TestClient, str, Path],
) -> None:
    client, vid, db = triage_client
    client.post(f"/inbox/{vid}/triage", data={"action": "dismiss"})
    p = get_packet(vid, db)
    assert p is not None
    assert p["severity"] == "info"


def test_triage_requires_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    db = tmp_path / "store.db"
    init_db(db)
    _seed_packet(db)
    app.state.key_store = str(tmp_path / "keys.json")
    app.state.output_dir = str(tmp_path)
    app.state.store_db = str(db)
    client = TestClient(app, follow_redirects=False)
    r = client.post("/inbox/vid-001/triage", data={"action": "dismiss"})
    assert r.status_code == 401
    p = get_packet("vid-001", db)
    assert p is not None
    assert p["triage_status"] == "new"
