"""Tests: approve/reject workflow for diff packets."""

from __future__ import annotations

import base64
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from assay._vendor.warden import WardenConfig, issue_token
from assay.auth.admin import hash_password
from assay.ingest.app import app as ingest_app
from assay.keys.store import create_key
from assay.store.db import (
    StoreError,
    list_packets,
    set_baseline,
    set_review_status,
)

_SECRET = "x" * 32
_EMAIL = "admin@test.com"


def _png_b64(color: tuple[int, int, int] = (100, 150, 200)) -> str:
    img = Image.new("RGB", (10, 10), color)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, str]:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    key_file = str(tmp_path / "keys.json")
    raw_key = create_key(key_file)
    ingest_app.state.key_store = key_file
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(tmp_path / "store.db")
    client = TestClient(ingest_app, follow_redirects=False)
    client.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return client, raw_key


def _ingest(client: TestClient, key: str, url: str, color: tuple[int, int, int]) -> str:
    resp = client.post(
        "/ingest",
        json={
            "captured_at": "2026-05-01T10:00:00Z",
            "url": url,
            "viewport": {"width": 10, "height": 10},
            "user_agent": "Mozilla/5.0",
            "screenshot": _png_b64(color),
        },
        headers={"X-Assay-Key": key},
    )
    assert resp.status_code == 200
    packets = list_packets(Path(ingest_app.state.store_db))
    return str(packets[-1]["verification_id"])


# --- store unit tests ---


def test_set_review_status_approved(tmp_path: Path) -> None:
    from assay.store.db import init_db, insert_packet

    db = tmp_path / "store.db"
    init_db(db)
    p: dict[str, object] = {
        "verification_id": "r001",
        "issue_type": "screenshot_evidence",
        "severity": "info",
        "outcome": "inconclusive",
        "summary": "test",
        "raw": "{}",
    }
    insert_packet(p, db)
    set_review_status("r001", "approved", db)
    packets = list_packets(db)
    assert packets[0]["review_status"] == "approved"


def test_set_review_status_rejected(tmp_path: Path) -> None:
    from assay.store.db import init_db, insert_packet

    db = tmp_path / "store.db"
    init_db(db)
    p: dict[str, object] = {
        "verification_id": "r002",
        "issue_type": "screenshot_evidence",
        "severity": "info",
        "outcome": "inconclusive",
        "summary": "test",
        "raw": "{}",
    }
    insert_packet(p, db)
    set_review_status("r002", "rejected", db)
    packets = list_packets(db)
    assert packets[0]["review_status"] == "rejected"


def test_set_review_status_invalid_raises(tmp_path: Path) -> None:
    from assay.store.db import init_db

    db = tmp_path / "store.db"
    init_db(db)
    with pytest.raises(StoreError, match="invalid review_status"):
        set_review_status("anything", "pending", db)


def test_set_review_status_missing_packet_raises(tmp_path: Path) -> None:
    from assay.store.db import init_db

    db = tmp_path / "store.db"
    init_db(db)
    with pytest.raises(StoreError, match="not found"):
        set_review_status("nonexistent", "approved", db)


# --- route tests ---


def test_approve_route_redirects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, key = _setup(tmp_path, monkeypatch)
    url = "https://example.com/approve"
    first_vid = _ingest(client, key, url, (0, 0, 0))
    set_baseline(first_vid, Path(ingest_app.state.store_db))
    second_vid = _ingest(client, key, url, (255, 255, 255))
    resp = client.post(f"/packet/{second_vid}/approve")
    assert resp.status_code == 303
    assert resp.headers["location"].endswith(f"/packet/{second_vid}")


def test_reject_route_redirects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, key = _setup(tmp_path, monkeypatch)
    url = "https://example.com/reject"
    first_vid = _ingest(client, key, url, (0, 0, 0))
    set_baseline(first_vid, Path(ingest_app.state.store_db))
    second_vid = _ingest(client, key, url, (255, 255, 255))
    resp = client.post(f"/packet/{second_vid}/reject")
    assert resp.status_code == 303
    assert resp.headers["location"].endswith(f"/packet/{second_vid}")


def test_approve_sets_baseline_and_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, key = _setup(tmp_path, monkeypatch)
    url = "https://example.com/approve2"
    first_vid = _ingest(client, key, url, (0, 0, 0))
    set_baseline(first_vid, Path(ingest_app.state.store_db))
    second_vid = _ingest(client, key, url, (255, 255, 255))
    client.post(f"/packet/{second_vid}/approve")
    from assay.store.db import list_baselines

    db = Path(ingest_app.state.store_db)
    baselines = list_baselines(db)
    assert baselines.get(url) == second_vid
    packets = list_packets(db)
    second = next(p for p in packets if str(p["verification_id"]) == second_vid)
    assert second["review_status"] == "approved"


def test_reject_sets_review_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, key = _setup(tmp_path, monkeypatch)
    url = "https://example.com/reject2"
    first_vid = _ingest(client, key, url, (0, 0, 0))
    set_baseline(first_vid, Path(ingest_app.state.store_db))
    second_vid = _ingest(client, key, url, (255, 255, 255))
    client.post(f"/packet/{second_vid}/reject")
    db = Path(ingest_app.state.store_db)
    packets = list_packets(db)
    second = next(p for p in packets if str(p["verification_id"]) == second_vid)
    assert second["review_status"] == "rejected"


def test_packet_detail_shows_approve_reject_buttons(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, key = _setup(tmp_path, monkeypatch)
    url = "https://example.com/buttons"
    first_vid = _ingest(client, key, url, (0, 0, 0))
    set_baseline(first_vid, Path(ingest_app.state.store_db))
    second_vid = _ingest(client, key, url, (255, 255, 255))
    resp = client.get(f"/packet/{second_vid}")
    assert resp.status_code == 200
    assert "Approve" in resp.text
    assert "Reject" in resp.text


def test_packet_detail_shows_approved_badge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, key = _setup(tmp_path, monkeypatch)
    url = "https://example.com/badge-approved"
    first_vid = _ingest(client, key, url, (0, 0, 0))
    set_baseline(first_vid, Path(ingest_app.state.store_db))
    second_vid = _ingest(client, key, url, (255, 255, 255))
    client.post(f"/packet/{second_vid}/approve")
    resp = client.get(f"/packet/{second_vid}")
    assert resp.status_code == 200
    assert "approved" in resp.text


def test_packet_detail_shows_regression_badge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, key = _setup(tmp_path, monkeypatch)
    url = "https://example.com/badge-rejected"
    first_vid = _ingest(client, key, url, (0, 0, 0))
    set_baseline(first_vid, Path(ingest_app.state.store_db))
    second_vid = _ingest(client, key, url, (255, 255, 255))
    client.post(f"/packet/{second_vid}/reject")
    resp = client.get(f"/packet/{second_vid}")
    assert resp.status_code == 200
    assert "regression" in resp.text
