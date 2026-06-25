"""Tests: diff attachment on /ingest when a baseline exists."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from assay._vendor.warden import WardenConfig, issue_token
from assay.auth.admin import hash_password
from assay.ingest.app import app as ingest_app
from assay.keys.store import create_key
from assay.store.db import set_baseline

_SECRET = "x" * 32
_EMAIL = "admin@test.com"


def _png_b64(color: tuple[int, int, int] = (100, 150, 200), size: tuple[int, int] = (10, 10)) -> str:
    import io

    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _setup_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, str]:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    db = tmp_path / "store.db"
    key_file = str(tmp_path / "keys.json")
    raw_key = create_key(key_file)
    ingest_app.state.key_store = key_file
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(db)
    client = TestClient(ingest_app, follow_redirects=False)
    client.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return client, raw_key


def _ingest(
    client: TestClient,
    raw_key: str,
    url: str = "https://example.com/page",
    color: tuple[int, int, int] = (100, 150, 200),
) -> dict[str, object]:
    payload = {
        "captured_at": "2026-05-01T10:00:00Z",
        "url": url,
        "viewport": {"width": 10, "height": 10},
        "user_agent": "Mozilla/5.0",
        "screenshot": _png_b64(color),
    }
    resp = client.post("/ingest", json=payload, headers={"X-Assay-Key": raw_key})
    assert resp.status_code == 200
    return dict(resp.json())


def test_ingest_without_baseline_has_no_diff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, raw_key = _setup_app(tmp_path, monkeypatch)
    _ingest(client, raw_key)
    from assay.store.db import list_packets

    db = tmp_path / "store.db"
    packets = list_packets(db)
    assert len(packets) == 1
    assert packets[0].get("diff_result") is None


def test_ingest_with_baseline_attaches_diff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, raw_key = _setup_app(tmp_path, monkeypatch)
    url = "https://example.com/page"

    _ingest(client, raw_key, url=url, color=(0, 0, 0))

    db = tmp_path / "store.db"
    packets_after_first = __import__("assay.store.db", fromlist=["list_packets"]).list_packets(db)
    first_vid = str(packets_after_first[0]["verification_id"])
    set_baseline(first_vid, db)

    _ingest(client, raw_key, url=url, color=(255, 255, 255))

    from assay.store.db import list_packets

    packets = list_packets(db)
    second = next(p for p in packets if str(p["verification_id"]) != first_vid)
    diff = second.get("diff_result")
    assert isinstance(diff, dict)
    assert diff["total_pixels"] == 100
    assert diff["changed_pixels"] == 100
    assert diff["diff_pct"] == 100.0
    diff_path = Path(str(diff["diff_image_path"]))
    assert diff_path.exists()


def test_packet_detail_shows_diff_section(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, raw_key = _setup_app(tmp_path, monkeypatch)
    url = "https://example.com/page"

    _ingest(client, raw_key, url=url, color=(0, 0, 0))
    db = tmp_path / "store.db"
    from assay.store.db import list_packets

    packets = list_packets(db)
    first_vid = str(packets[0]["verification_id"])
    set_baseline(first_vid, db)

    _ingest(client, raw_key, url=url, color=(255, 0, 0))

    packets = list_packets(db)
    second_vid = str(next(p for p in packets if str(p["verification_id"]) != first_vid)["verification_id"])

    resp = client.get(f"/packet/{second_vid}")
    assert resp.status_code == 200
    assert "Diff vs Baseline" in resp.text
    assert "changed" in resp.text
