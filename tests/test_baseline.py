"""Tests: baselines table — set, get, overwrite, list + route tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from warden import WardenConfig, issue_token

from assay.auth.admin import hash_password
from assay.ingest.app import app as ingest_app
from assay.store.db import (
    StoreError,
    get_baseline_for_url,
    init_db,
    insert_packet,
    list_baselines,
    set_baseline,
)

_PACKET_A: dict[str, object] = {
    "verification_id": "aaa-0001",
    "task_id": "TASK-0001",
    "issue_type": "test_result",
    "severity": "low",
    "outcome": "pass",
    "summary": "baseline test packet A",
    "artifact_refs": [],
    "followup_candidates": [],
    "verified_at": "2026-05-01T10:00:00Z",
    "url": "https://example.com/page",
    "raw": "{}",
}

_PACKET_B: dict[str, object] = {
    **_PACKET_A,  # type: ignore[misc]
    "verification_id": "bbb-0002",
    "summary": "baseline test packet B",
}

_SECRET = "x" * 32
_EMAIL = "admin@test.com"


def _db(tmp_path: Path) -> Path:
    db = tmp_path / "store.db"
    init_db(db)
    return db


def _setup_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    db = tmp_path / "store.db"
    ingest_app.state.key_store = str(tmp_path / "keys.json")
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(db)
    client = TestClient(ingest_app, follow_redirects=False)
    client.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return client


# --- store unit tests ---


def test_set_baseline_returns_url(tmp_path: Path) -> None:
    db = _db(tmp_path)
    insert_packet(_PACKET_A, db)
    url = set_baseline("aaa-0001", db)
    assert url == "https://example.com/page"


def test_get_baseline_for_url_returns_packet(tmp_path: Path) -> None:
    db = _db(tmp_path)
    insert_packet(_PACKET_A, db)
    set_baseline("aaa-0001", db)
    result = get_baseline_for_url("https://example.com/page", db)
    assert result is not None
    assert result["verification_id"] == "aaa-0001"


def test_set_baseline_overwrites_previous(tmp_path: Path) -> None:
    db = _db(tmp_path)
    insert_packet(_PACKET_A, db)
    insert_packet(_PACKET_B, db)
    set_baseline("aaa-0001", db)
    set_baseline("bbb-0002", db)
    result = get_baseline_for_url("https://example.com/page", db)
    assert result is not None
    assert result["verification_id"] == "bbb-0002"


def test_list_baselines_returns_mapping(tmp_path: Path) -> None:
    db = _db(tmp_path)
    insert_packet(_PACKET_A, db)
    set_baseline("aaa-0001", db)
    mapping = list_baselines(db)
    assert mapping == {"https://example.com/page": "aaa-0001"}


def test_list_baselines_empty_when_no_db(tmp_path: Path) -> None:
    missing = tmp_path / "missing.db"
    assert list_baselines(missing) == {}


def test_get_baseline_returns_none_when_no_baseline_set(tmp_path: Path) -> None:
    db = _db(tmp_path)
    insert_packet(_PACKET_A, db)
    assert get_baseline_for_url("https://example.com/page", db) is None


def test_get_baseline_returns_none_when_no_db(tmp_path: Path) -> None:
    missing = tmp_path / "missing.db"
    assert get_baseline_for_url("https://example.com/page", missing) is None


def test_set_baseline_raises_for_missing_packet(tmp_path: Path) -> None:
    db = _db(tmp_path)
    with pytest.raises(StoreError, match="not found"):
        set_baseline("nonexistent-id", db)


def test_set_baseline_raises_for_packet_without_url(tmp_path: Path) -> None:
    db = _db(tmp_path)
    no_url: dict[str, object] = {**_PACKET_A, "verification_id": "ccc-0003", "url": ""}  # type: ignore[misc]
    insert_packet(no_url, db)
    with pytest.raises(StoreError, match="no url field"):
        set_baseline("ccc-0003", db)


# --- route tests ---


def test_set_baseline_route_redirects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_PACKET_A, db)
    client = _setup_app(tmp_path, monkeypatch)
    resp = client.post("/packet/aaa-0001/set-baseline")
    assert resp.status_code == 303
    assert resp.headers["location"].endswith("/packet/aaa-0001")


def test_set_baseline_route_missing_packet_still_redirects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _setup_app(tmp_path, monkeypatch)
    resp = client.post("/packet/nonexistent/set-baseline")
    assert resp.status_code == 303
    assert resp.headers["location"].endswith("/packet/nonexistent")


def test_dashboard_shows_baseline_badge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_PACKET_A, db)
    set_baseline("aaa-0001", db)
    client = _setup_app(tmp_path, monkeypatch)
    resp = client.get("/")
    assert resp.status_code == 200
    assert 'class="baseline-badge"' in resp.text


def test_dashboard_no_badge_without_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_PACKET_A, db)
    client = _setup_app(tmp_path, monkeypatch)
    resp = client.get("/")
    assert resp.status_code == 200
    assert 'class="baseline-badge"' not in resp.text


def test_packet_detail_shows_set_baseline_button(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_PACKET_A, db)
    client = _setup_app(tmp_path, monkeypatch)
    resp = client.get("/packet/aaa-0001")
    assert resp.status_code == 200
    assert "Set as baseline" in resp.text


def test_packet_detail_shows_current_baseline_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "store.db"
    init_db(db)
    insert_packet(_PACKET_A, db)
    set_baseline("aaa-0001", db)
    client = _setup_app(tmp_path, monkeypatch)
    resp = client.get("/packet/aaa-0001")
    assert resp.status_code == 200
    assert "current baseline" in resp.text
    assert "Set as baseline" not in resp.text
