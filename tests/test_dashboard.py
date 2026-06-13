"""Tests: GET / dashboard route on the ingest FastAPI app."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from warden import WardenConfig, issue_token

from assay.auth.admin import hash_password
from assay.ingest.app import app as ingest_app
from assay.keys.store import create_key
from assay.store.db import init_db, insert_packet

_PACKET: dict[str, object] = {
    "verification_id": "dddd-0004",
    "task_id": "TASK-0001",
    "issue_type": "test_result",
    "severity": "low",
    "outcome": "pass",
    "summary": "dashboard test packet",
    "artifact_refs": [],
    "followup_candidates": [],
    "verified_at": "2026-05-01T10:00:00Z",
    "raw": "{}",
}

_SECRET = "x" * 32
_EMAIL = "admin@test.com"


def _setup_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    db = tmp_path / "store.db"
    key_file = str(tmp_path / "keys.json")
    ingest_app.state.key_store = key_file
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(db)
    client = TestClient(ingest_app, follow_redirects=False)
    client.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return client


def test_dashboard_returns_200(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup_app(tmp_path, monkeypatch)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_dashboard_contains_packet_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_PACKET, db)
    client = _setup_app(tmp_path, monkeypatch)

    resp = client.get("/")
    assert resp.status_code == 200
    assert "dddd-0004" in resp.text
    assert "dashboard test packet" in resp.text
    assert "pass" in resp.text


def test_dashboard_empty_store_shows_no_packets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup_app(tmp_path, monkeypatch)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "no packets" in resp.text


def test_dashboard_summary_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet({**_PACKET, "verification_id": "e001", "outcome": "pass"}, db)
    insert_packet({**_PACKET, "verification_id": "e002", "outcome": "fail"}, db)
    insert_packet({**_PACKET, "verification_id": "e003", "outcome": "fail"}, db)
    client = _setup_app(tmp_path, monkeypatch)

    resp = client.get("/")
    assert "3 total" in resp.text
    assert "1 pass" in resp.text
    assert "2 fail" in resp.text


def test_dashboard_screenshot_yes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    png = str(tmp_path / "dddd-0004.png")
    insert_packet({**_PACKET, "artifact_refs": [png]}, db)
    client = _setup_app(tmp_path, monkeypatch)

    resp = client.get("/")
    assert "yes" in resp.text


def test_dashboard_screenshot_no(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet({**_PACKET, "artifact_refs": []}, db)
    client = _setup_app(tmp_path, monkeypatch)

    resp = client.get("/")
    assert "no" in resp.text


def test_ingest_post_still_works_after_dashboard_route(tmp_path: Path) -> None:
    key_file = str(tmp_path / "keys.json")
    raw_key = create_key(key_file)
    db = tmp_path / "store.db"
    ingest_app.state.key_store = key_file
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(db)
    client = TestClient(ingest_app)

    payload = {
        "captured_at": "2026-05-01T10:00:00Z",
        "url": "https://example.com",
        "viewport": {"width": 1280, "height": 800},
        "user_agent": "Mozilla/5.0",
        "screenshot": base64.b64encode(b"fake-png").decode(),
    }
    resp = client.post("/ingest", json=payload, headers={"X-Assay-Key": raw_key})
    assert resp.status_code == 200
