"""Tests: GET / dashboard route on the ingest FastAPI app."""

from __future__ import annotations

import base64
from pathlib import Path

from fastapi.testclient import TestClient

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


def _setup_app(tmp_path: Path) -> TestClient:
    db = tmp_path / "store.db"
    key_file = str(tmp_path / "keys.json")
    ingest_app.state.key_store = key_file
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(db)
    return TestClient(ingest_app)


def test_dashboard_returns_200(tmp_path: Path) -> None:
    client = _setup_app(tmp_path)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_dashboard_contains_packet_data(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_PACKET, db)
    client = _setup_app(tmp_path)

    resp = client.get("/")
    assert resp.status_code == 200
    assert "dddd-0004" in resp.text
    assert "dashboard test packet" in resp.text
    assert "pass" in resp.text


def test_dashboard_empty_store_shows_no_packets(tmp_path: Path) -> None:
    client = _setup_app(tmp_path)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "no packets" in resp.text


def test_dashboard_summary_counts(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet({**_PACKET, "verification_id": "e001", "outcome": "pass"}, db)
    insert_packet({**_PACKET, "verification_id": "e002", "outcome": "fail"}, db)
    insert_packet({**_PACKET, "verification_id": "e003", "outcome": "fail"}, db)
    client = _setup_app(tmp_path)

    resp = client.get("/")
    assert "3 total" in resp.text
    assert "1 pass" in resp.text
    assert "2 fail" in resp.text


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
