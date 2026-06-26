from __future__ import annotations

import importlib
import sys

import pytest
from fastapi.testclient import TestClient

_SECRET = "x" * 32
_GATE_LOGIN = "https://gate.diwata.domains/login"


def _reload_app() -> object:
    importlib.import_module("assay.ingest.app")
    return importlib.reload(sys.modules["assay.ingest.app"])


@pytest.fixture()
def gate_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """App that delegates auth to Gate (ASSAY_LOGIN_URL set)."""
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    monkeypatch.setenv("ASSAY_LOGIN_URL", _GATE_LOGIN)
    app_module = _reload_app()
    try:
        yield TestClient(app_module.app, follow_redirects=False)
    finally:
        monkeypatch.delenv("ASSAY_LOGIN_URL", raising=False)
        _reload_app()


@pytest.fixture()
def default_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """App with no ASSAY_LOGIN_URL — defaults to local /login route."""
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    monkeypatch.delenv("ASSAY_LOGIN_URL", raising=False)
    app_module = _reload_app()
    try:
        yield TestClient(app_module.app, follow_redirects=False)
    finally:
        _reload_app()


def test_login_redirects_to_gate(gate_client: TestClient) -> None:
    r = gate_client.get("/login")
    assert r.status_code == 303
    assert r.headers["location"] == _GATE_LOGIN


def test_login_no_local_form_rendered(gate_client: TestClient) -> None:
    r = gate_client.get("/login")
    # Delegated login is a redirect, not an HTML form.
    assert "<form" not in r.text


def test_login_unconfigured_returns_503_not_loop(default_client: TestClient) -> None:
    # With the local default (SSO not configured), /login must NOT self-redirect
    # (that would be an infinite loop); it returns 503 instead.
    r = default_client.get("/login")
    assert r.status_code == 503
    assert "ASSAY_LOGIN_URL" in r.json()["detail"]


def test_logout_clears_cookie_and_redirects_to_gate(
    gate_client: TestClient,
) -> None:
    r = gate_client.get("/logout")
    assert r.status_code == 303
    assert r.headers["location"] == _GATE_LOGIN
    set_cookie = r.headers.get("set-cookie", "")
    assert "warden_session=" in set_cookie
