from __future__ import annotations

import importlib
import sys
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from assay._vendor.warden import WardenConfig, issue_token

_EMAIL = "admin@example.com"
_SECRET = "x" * 32
_GATE_LOGIN = "https://gate.diwata.domains/login"


def _reload_app() -> object:
    importlib.import_module("assay.ingest.app")
    return importlib.reload(sys.modules["assay.ingest.app"])


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """App configured to delegate auth to Gate via ASSAY_LOGIN_URL."""
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    monkeypatch.setenv("ASSAY_LOGIN_URL", _GATE_LOGIN)
    app_module = _reload_app()
    try:
        yield TestClient(app_module.app, follow_redirects=False)
    finally:
        # Restore default LOGIN_URL binding for other test modules.
        monkeypatch.delenv("ASSAY_LOGIN_URL", raising=False)
        _reload_app()


def _session_cookie() -> str:
    return issue_token(_EMAIL, WardenConfig(secret=_SECRET))


def test_protected_path_redirects_to_gate_with_next(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 303
    expected_next = quote("http://testserver/", safe="")
    assert r.headers["location"] == f"{_GATE_LOGIN}?next={expected_next}"


def test_packet_detail_redirects_to_gate_with_next(client: TestClient) -> None:
    r = client.get("/packet/some-id")
    assert r.status_code == 303
    expected_next = quote("http://testserver/packet/some-id", safe="")
    assert r.headers["location"] == f"{_GATE_LOGIN}?next={expected_next}"


def test_protected_path_preserves_query_in_next(client: TestClient) -> None:
    r = client.get("/keys?foo=bar")
    assert r.status_code == 303
    expected_next = quote("http://testserver/keys?foo=bar", safe="")
    assert r.headers["location"] == f"{_GATE_LOGIN}?next={expected_next}"


def test_login_redirects_to_gate(client: TestClient) -> None:
    r = client.get("/login")
    assert r.status_code == 303
    assert r.headers["location"] == _GATE_LOGIN


def test_logout_clears_cookie_and_redirects_to_gate(client: TestClient) -> None:
    client.cookies.set("warden_session", _session_cookie())
    r = client.get("/logout")
    assert r.status_code == 303
    assert r.headers["location"] == _GATE_LOGIN
    set_cookie = r.headers.get("set-cookie", "")
    assert "warden_session=" in set_cookie
    assert ('Max-Age=0' in set_cookie) or ('expires=' in set_cookie.lower())


def test_ingest_accessible_without_session(client: TestClient) -> None:
    r = client.post("/ingest", json={}, headers={"X-Assay-Key": "any"})
    assert r.status_code != 303


def test_status_accessible_without_session(client: TestClient) -> None:
    r = client.get("/status/VERIFY-TEST-001")
    assert r.status_code != 303


def test_dashboard_accessible_with_valid_session(client: TestClient) -> None:
    client.cookies.set("warden_session", _session_cookie())
    r = client.get("/")
    assert r.status_code == 200


def test_invalid_token_redirects_to_gate(client: TestClient) -> None:
    client.cookies.set("warden_session", "not.a.valid.token")
    r = client.get("/")
    assert r.status_code == 303
    assert r.headers["location"].startswith(f"{_GATE_LOGIN}?next=")
