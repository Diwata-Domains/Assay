"""Tests: GET /packet/{verification_id} detail route."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from assay._vendor.warden import WardenConfig, issue_token
from assay.auth.admin import hash_password
from assay.ingest.app import app as ingest_app
from assay.store.db import init_db, insert_packet

_PACKET: dict[str, object] = {
    "verification_id": "eeee-0005",
    "task_id": "TASK-0001",
    "issue_type": "test_result",
    "severity": "low",
    "outcome": "pass",
    "summary": "detail view test packet",
    "artifact_refs": [],
    "followup_candidates": [],
    "verified_at": "2026-05-01T10:00:00Z",
    "raw": "{}",
}

_SECRET = "x" * 32
_EMAIL = "admin@test.com"


def _setup_app(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    packets: Optional[list[dict]] = None,  # type: ignore[type-arg]
) -> TestClient:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    db = tmp_path / "store.db"
    key_file = str(tmp_path / "keys.json")
    ingest_app.state.key_store = key_file
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(db)
    init_db(db)
    for p in (packets or []):
        insert_packet(p, db)
    client = TestClient(ingest_app, follow_redirects=False)
    client.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return client


def test_packet_detail_returns_200(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup_app(tmp_path, monkeypatch, [_PACKET])
    resp = client.get("/packet/eeee-0005")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_packet_detail_shows_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup_app(tmp_path, monkeypatch, [_PACKET])
    resp = client.get("/packet/eeee-0005")
    assert "detail view test packet" in resp.text
    assert "pass" in resp.text
    assert "eeee-0005" in resp.text


def test_packet_detail_inline_screenshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    png = tmp_path / "eeee-0005.png"
    png.write_bytes(b"\x89PNG")
    packet = {**_PACKET, "artifact_refs": [str(png)]}
    client = _setup_app(tmp_path, monkeypatch, [packet])

    resp = client.get("/packet/eeee-0005")
    assert resp.status_code == 200
    assert "data:image/png;base64," in resp.text


def test_packet_detail_no_screenshot_when_file_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    packet = {**_PACKET, "artifact_refs": [str(tmp_path / "missing.png")]}
    client = _setup_app(tmp_path, monkeypatch, [packet])

    resp = client.get("/packet/eeee-0005")
    assert resp.status_code == 200
    assert "data:image/png;base64," not in resp.text


def test_packet_detail_404_for_unknown_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _setup_app(tmp_path, monkeypatch)
    resp = client.get("/packet/does-not-exist")
    assert resp.status_code == 404
    assert "not found" in resp.text
