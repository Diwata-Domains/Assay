"""Tests: GET /status/{verification_id} endpoint."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from assay.ingest.app import app as ingest_app
from assay.store.db import init_db, insert_packet

_PACKET: dict[str, object] = {
    "verification_id": "VERIFY-0041-001",
    "task_id": "TASK-0041",
    "issue_type": "test_result",
    "severity": "info",
    "outcome": "pass",
    "summary": "status endpoint test",
    "artifact_refs": [],
    "followup_candidates": [],
    "verified_at": "2026-05-08T10:00:00Z",
    "raw": "{}",
}


def _setup_app(tmp_path: Path, packets: list[dict] | None = None) -> TestClient:
    db = tmp_path / "store.db"
    ingest_app.state.key_store = str(tmp_path / "keys.json")
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(db)
    init_db(db)
    for p in (packets or []):
        insert_packet(p, db)
    return TestClient(ingest_app)


def test_status_returns_complete_when_found(tmp_path: Path) -> None:
    client = _setup_app(tmp_path, [_PACKET])
    resp = client.get("/status/VERIFY-0041-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "complete"
    assert data["outcome"] == "pass"
    assert data["verification_id"] == "VERIFY-0041-001"


def test_status_returns_verified_at(tmp_path: Path) -> None:
    client = _setup_app(tmp_path, [_PACKET])
    resp = client.get("/status/VERIFY-0041-001")
    assert resp.status_code == 200
    assert resp.json()["verified_at"] == "2026-05-08T10:00:00Z"


def test_status_404_for_unknown_id(tmp_path: Path) -> None:
    client = _setup_app(tmp_path)
    resp = client.get("/status/VERIFY-9999-999")
    assert resp.status_code == 404
    assert resp.json()["status"] == "not_found"


def test_status_includes_task_id_and_summary(tmp_path: Path) -> None:
    client = _setup_app(tmp_path, [_PACKET])
    resp = client.get("/status/VERIFY-0041-001")
    data = resp.json()
    assert data["task_id"] == "TASK-0041"
    assert data["summary"] == "status endpoint test"
