"""Tests: API-key authenticated headless baseline endpoints (/baselines*)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from assay.ingest.app import app as ingest_app
from assay.keys.store import create_key
from assay.store import db as store

_PACKET: dict[str, object] = {
    "verification_id": "VERIFY-0050-001",
    "task_id": "TASK-0050",
    "issue_type": "test_failure",
    "severity": "info",
    "outcome": "pass",
    "summary": "baseline http test",
    "artifact_refs": [],
    "followup_candidates": [],
    "verified_at": "2026-06-25T10:00:00Z",
    "url": "https://example.com/page",
    "raw": "{}",
}


def _setup(tmp_path: Path) -> tuple[TestClient, str]:
    key_store = tmp_path / "keys.json"
    raw = create_key(str(key_store), label="agent")
    db = tmp_path / "store.db"
    ingest_app.state.key_store = str(key_store)
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(db)
    store.init_db(db)
    store.insert_packet(_PACKET, db)
    return TestClient(ingest_app), raw


def test_baselines_list_requires_key(tmp_path: Path) -> None:
    client, _ = _setup(tmp_path)
    assert client.get("/baselines").status_code == 401


def test_baselines_set_then_list(tmp_path: Path) -> None:
    client, key = _setup(tmp_path)
    resp = client.post(
        "/baselines/set",
        headers={"X-Assay-Key": key},
        json={"verification_id": "VERIFY-0050-001"},
    )
    assert resp.status_code == 200
    assert resp.json()["url"] == "https://example.com/page"

    listed = client.get("/baselines", headers={"X-Assay-Key": key}).json()["baselines"]
    assert listed == [{"url": "https://example.com/page", "verification_id": "VERIFY-0050-001"}]


def test_baselines_approve(tmp_path: Path) -> None:
    client, key = _setup(tmp_path)
    resp = client.post(
        "/baselines/approve",
        headers={"X-Assay-Key": key},
        json={"verification_id": "VERIFY-0050-001"},
    )
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "approved"


def test_baselines_reject(tmp_path: Path) -> None:
    client, key = _setup(tmp_path)
    resp = client.post(
        "/baselines/reject",
        headers={"X-Assay-Key": key},
        json={"verification_id": "VERIFY-0050-001"},
    )
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "rejected"


def test_baselines_set_unknown_returns_404(tmp_path: Path) -> None:
    client, key = _setup(tmp_path)
    resp = client.post(
        "/baselines/set",
        headers={"X-Assay-Key": key},
        json={"verification_id": "missing"},
    )
    assert resp.status_code == 404
