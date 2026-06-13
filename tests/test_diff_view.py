"""Tests: before/after slider in packet detail view."""

from __future__ import annotations

import base64
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from warden import WardenConfig, issue_token

from assay.auth.admin import hash_password
from assay.ingest.app import app as ingest_app
from assay.keys.store import create_key
from assay.store.db import set_baseline

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
    from assay.store.db import list_packets

    db = ingest_app.state.store_db
    packets = list_packets(Path(db))
    return str(packets[-1]["verification_id"])


def test_packet_without_diff_shows_screenshot_not_slider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, key = _setup(tmp_path, monkeypatch)
    vid = _ingest(client, key, "https://example.com/", (0, 128, 255))
    resp = client.get(f"/packet/{vid}")
    assert resp.status_code == 200
    assert "slider-wrap" not in resp.text
    assert "Screenshot" in resp.text


def test_packet_with_diff_shows_slider(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, key = _setup(tmp_path, monkeypatch)
    url = "https://example.com/page"
    first_vid = _ingest(client, key, url, (0, 0, 0))
    set_baseline(first_vid, Path(ingest_app.state.store_db))
    second_vid = _ingest(client, key, url, (255, 255, 255))
    resp = client.get(f"/packet/{second_vid}")
    assert resp.status_code == 200
    assert "slider-wrap" in resp.text
    assert "sl-c" in resp.text


def test_slider_has_tab_buttons(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, key = _setup(tmp_path, monkeypatch)
    url = "https://example.com/tabs"
    first_vid = _ingest(client, key, url, (10, 20, 30))
    set_baseline(first_vid, Path(ingest_app.state.store_db))
    second_vid = _ingest(client, key, url, (200, 100, 50))
    resp = client.get(f"/packet/{second_vid}")
    assert "Slider" in resp.text
    assert "Highlight" in resp.text
    assert "Side by side" in resp.text


def test_slider_has_side_by_side_panel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, key = _setup(tmp_path, monkeypatch)
    url = "https://example.com/sbs"
    first_vid = _ingest(client, key, url, (5, 5, 5))
    set_baseline(first_vid, Path(ingest_app.state.store_db))
    second_vid = _ingest(client, key, url, (250, 250, 250))
    resp = client.get(f"/packet/{second_vid}")
    assert "dp-sbs" in resp.text
    assert "Before (baseline)" in resp.text
    assert "After (new capture)" in resp.text


def test_diff_stats_shown_in_slider_view(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client, key = _setup(tmp_path, monkeypatch)
    url = "https://example.com/stats"
    first_vid = _ingest(client, key, url, (0, 0, 0))
    set_baseline(first_vid, Path(ingest_app.state.store_db))
    second_vid = _ingest(client, key, url, (255, 255, 255))
    resp = client.get(f"/packet/{second_vid}")
    assert "diff-stats" in resp.text
    assert "changed" in resp.text
