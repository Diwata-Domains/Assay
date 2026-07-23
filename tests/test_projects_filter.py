"""GET /api/packets filters by project_id and surfaces it per row."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from assay._vendor.warden import WardenConfig, issue_token
from assay.ingest.app import app
from assay.keys.store import create_key

_SCREENSHOT = base64.b64encode(b"png").decode()
_SECRET = "x" * 32
_EMAIL = "admin@test.com"


def _payload(url: str) -> dict[str, object]:
    return {
        "captured_at": "2026-07-23T10:00:00Z",
        "url": url,
        "viewport": {"width": 1440, "height": 900},
        "user_agent": "Mozilla/5.0",
        "screenshot": _SCREENSHOT,
        "user_comment": "x",
        "metadata": {},
    }


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, str]:
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    store = str(tmp_path / "keys.json")
    app.state.key_store = store
    app.state.store_db = str(tmp_path / "store.db")
    app.state.output_dir = str(tmp_path / "output")
    c = TestClient(app)
    c.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return c, store


def test_packets_filtered_by_project(client: tuple[TestClient, str]) -> None:
    c, store = client
    key_a = create_key(store, label="a", project_id="proj-a")
    key_b = create_key(store, label="b", project_id="proj-b")
    c.post("/ingest", json=_payload("https://a.example"), headers={"X-Assay-Key": key_a})
    c.post("/ingest", json=_payload("https://b.example"), headers={"X-Assay-Key": key_b})

    r = c.get("/api/packets?project_id=proj-a")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["packets"], "expected the filtered packet"
    assert all(p["project_id"] == "proj-a" for p in body["packets"])
