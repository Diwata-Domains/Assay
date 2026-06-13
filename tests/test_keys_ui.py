from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from warden import WardenConfig, issue_token

from assay.auth.admin import hash_password
from assay.ingest.app import app as ingest_app

_SECRET = "x" * 32
_EMAIL = "admin@test.com"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password("pw"))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    ingest_app.state.key_store = str(tmp_path / "keys.json")
    ingest_app.state.output_dir = str(tmp_path)
    ingest_app.state.store_db = str(tmp_path / "store.db")
    c = TestClient(ingest_app, follow_redirects=False)
    c.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return c


def test_keys_page_renders(client: TestClient) -> None:
    r = client.get("/keys")
    assert r.status_code == 200
    assert "API Keys" in r.text
    assert "Create key" in r.text


def test_keys_page_no_active_keys(client: TestClient) -> None:
    r = client.get("/keys")
    assert "no active keys" in r.text


def test_create_key_shows_raw_value(client: TestClient) -> None:
    r = client.post("/keys", data={"label": "crm-test"})
    assert r.status_code == 200
    assert "crm-test" in r.text
    assert "copy it now" in r.text


def test_create_key_appears_in_list(client: TestClient) -> None:
    client.post("/keys", data={"label": "my-key"})
    r = client.get("/keys")
    assert "my-key" in r.text


def test_revoke_key_redirects(client: TestClient) -> None:
    from assay.keys.store import create_key, list_keys

    key_store = ingest_app.state.key_store
    create_key(key_store, "revoke-me")
    keys = list_keys(key_store)
    key_id = str(keys[0]["id"])

    r = client.post(f"/keys/{key_id}/revoke")
    assert r.status_code == 303
    assert r.headers["location"] == "/keys"


def test_revoke_key_removes_from_active_list(client: TestClient) -> None:
    from assay.keys.store import create_key, list_keys

    key_store = ingest_app.state.key_store
    create_key(key_store, "to-revoke")
    keys = list_keys(key_store)
    key_id = str(keys[0]["id"])

    client.post(f"/keys/{key_id}/revoke")
    r = client.get("/keys")
    assert "to-revoke" not in r.text


def test_revoke_unknown_key_redirects_gracefully(client: TestClient) -> None:
    r = client.post("/keys/does-not-exist/revoke")
    assert r.status_code == 303
