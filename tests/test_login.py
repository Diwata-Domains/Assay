from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from assay.auth.admin import hash_password
from assay.ingest.app import app

_EMAIL = "admin@example.com"
_PASSWORD = "correcthorse"
_SECRET = "x" * 32


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ASSAY_ADMIN_EMAIL", _EMAIL)
    monkeypatch.setenv("ASSAY_ADMIN_PASSWORD_HASH", hash_password(_PASSWORD))
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    return TestClient(app, follow_redirects=False)


def test_login_page_renders(client: TestClient) -> None:
    r = client.get("/login")
    assert r.status_code == 200
    assert "Sign in" in r.text
    assert "Assay" in r.text


def test_login_success_redirects_to_dashboard(client: TestClient) -> None:
    r = client.post("/login", data={"email": _EMAIL, "password": _PASSWORD})
    assert r.status_code == 303
    assert r.headers["location"] == "/"
    assert "warden_session" in r.cookies


def test_login_sets_httponly_cookie(client: TestClient) -> None:
    r = client.post("/login", data={"email": _EMAIL, "password": _PASSWORD})
    set_cookie = r.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie


def test_login_wrong_password(client: TestClient) -> None:
    r = client.post("/login", data={"email": _EMAIL, "password": "wrongpassword"})
    assert r.status_code == 401
    assert "Invalid email or password" in r.text
    assert "warden_session" not in r.cookies


def test_login_wrong_email(client: TestClient) -> None:
    r = client.post("/login", data={"email": "other@example.com", "password": _PASSWORD})
    assert r.status_code == 401
    assert "Invalid email or password" in r.text


def test_logout_clears_cookie(client: TestClient) -> None:
    login = client.post("/login", data={"email": _EMAIL, "password": _PASSWORD})
    session_cookie = login.cookies["warden_session"]
    client.cookies.set("warden_session", session_cookie)
    r = client.get("/logout")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_login_missing_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASSAY_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ASSAY_ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.delenv("WARDEN_SECRET", raising=False)
    c = TestClient(app, follow_redirects=False)
    r = c.post("/login", data={"email": _EMAIL, "password": _PASSWORD})
    assert r.status_code == 500
    assert "misconfigured" in r.text
