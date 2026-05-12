from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from assay.auth.admin import create_token, hash_password
from assay.ingest.app import app

_EMAIL = "admin@example.com"
_PASSWORD = "correcthorse"
_SECRET = "x" * 32


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password(_PASSWORD))
    monkeypatch.setenv("ASSAY_JWT_SECRET", _SECRET)
    return TestClient(app, follow_redirects=False)


def _session_cookie(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("ASSAY_JWT_SECRET", _SECRET)
    return create_token(_EMAIL)


def test_dashboard_redirects_without_session(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_packet_detail_redirects_without_session(client: TestClient) -> None:
    r = client.get("/packet/some-id")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_keys_redirects_without_session(client: TestClient) -> None:
    r = client.get("/keys")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_login_page_accessible_without_session(client: TestClient) -> None:
    r = client.get("/login")
    assert r.status_code == 200


def test_ingest_accessible_without_session(client: TestClient) -> None:
    r = client.post("/ingest", json={}, headers={"X-Assay-Key": "any"})
    assert r.status_code != 303


def test_status_accessible_without_session(client: TestClient) -> None:
    r = client.get("/status/VERIFY-TEST-001")
    assert r.status_code != 303


def test_dashboard_accessible_with_valid_session(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = _session_cookie(monkeypatch)
    client.cookies.set("assay_session", token)
    r = client.get("/")
    assert r.status_code == 200


def test_invalid_token_redirects_to_login(client: TestClient) -> None:
    client.cookies.set("assay_session", "not.a.valid.token")
    r = client.get("/")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
