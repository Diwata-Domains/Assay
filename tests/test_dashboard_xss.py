"""Tests: attacker-controlled packet fields are HTML-escaped in the dashboard."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from assay._vendor.warden import WardenConfig, issue_token
from assay.auth.admin import hash_password
from assay.ingest.app import app as ingest_app
from assay.store.db import init_db, insert_packet

_SECRET = "x" * 32
_EMAIL = "admin@test.com"
_XSS = "<script>alert('x')</script>"

_PACKET_XSS: dict[str, object] = {
    "verification_id": "eeee-0001",
    "task_id": _XSS,
    "issue_type": "test_result",
    "severity": "low",
    "outcome": "pass",
    "summary": _XSS,
    "url": "https://evil.example/<script>alert(1)</script>",
    "artifact_refs": [],
    "followup_candidates": [],
    "verified_at": "2026-05-01T10:00:00Z",
    "raw": "{}",
}


def _setup_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_PACKET_XSS, db)
    ingest_app.state.key_store = str(tmp_path / "keys.json")
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(db)
    client = TestClient(ingest_app, follow_redirects=False)
    client.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return client


def test_dashboard_list_escapes_packet_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup_app(tmp_path, monkeypatch)
    resp = client.get("/legacy")
    assert resp.status_code == 200
    assert _XSS not in resp.text
    assert "&lt;script&gt;" in resp.text


def test_packet_detail_escapes_packet_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup_app(tmp_path, monkeypatch)
    resp = client.get("/packet/eeee-0001")
    assert resp.status_code == 200
    assert _XSS not in resp.text
    assert "&lt;script&gt;" in resp.text
