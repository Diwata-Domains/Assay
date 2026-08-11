"""Assay code-handoff SSO (Phase 0a) — the diwata.id-ready sign-in path.

Assay is a server-rendered console: its session middleware redirects
unauthenticated browsers, and the /dashboard SPA merely bounces 401s to the
server's /login. So the whole handoff is server-driven — no keeper table (a
gate-verified identity IS the authorization, like Apex/Daemon). These tests prove
Assay's half of one_login_spec.md §4:

  /login (or a page-load deny) → 303 to the gate with client_id + registered
  callback + a state cookie → GET /auth/callback?code=&state= redeems the code
  server-side → mints Assay's OWN ``assay_session`` cookie → that cookie
  authenticates protected routes,

plus the transition fallback that keeps live shared ``warden_session`` sessions
alive, and sign-out clearing both cookies.

The gate's network exchange (warden.gate.exchange_code, vendored) is
monkeypatched, so no live gate is needed. ASSAY_GATE_SSO is read from os.environ
per request, so flipping it is just setenv.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from assay._vendor.warden import WardenConfig, issue_token
from assay._vendor.warden.gate import GateExchangeError
from assay.ingest import gate_sso
from assay.ingest.app import app
from assay.ingest.gate_sso import ASSAY_COOKIE_NAME, SHARED_COOKIE_NAME, STATE_COOKIE_NAME
from assay.store.db import init_db, insert_project

_SECRET = "assay-code-handoff-secret-assay-code-handoff"
_EMAIL = "ss@diwata.domains"


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """WARDEN_SECRET for signing; non-Secure cookies so the http test client
    resends them; a known gate origin. Flag OFF by default."""
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    monkeypatch.setenv("WARDEN_SECURE_COOKIE", "false")
    monkeypatch.setenv("GATE_PUBLIC_ORIGIN", "https://gate.diwata.domains")
    monkeypatch.delenv("ASSAY_GATE_SSO", raising=False)
    db = str(tmp_path / "store.db")
    app.state.store_db = db
    app.state.key_store = str(tmp_path / "keys.json")
    app.state.output_dir = str(tmp_path / "output")
    init_db(Path(db))
    insert_project("CRM", db_path=Path(db))


def _enable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASSAY_GATE_SSO", "true")
    monkeypatch.setenv("GATE_CLIENT_SECRET_ASSAY", "test-assay-exchange-secret")


def _stub_exchange(monkeypatch: pytest.MonkeyPatch, identity: dict) -> None:
    async def _fake_exchange(config, code, redirect_uri):  # noqa: ANN001
        return identity

    monkeypatch.setattr(gate_sso, "exchange_code", _fake_exchange)


def _client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False, follow_redirects=False)


# --- the flag gates the door ------------------------------------------------


def test_callback_404_when_disabled(env) -> None:
    # flag off (fixture default) — the redemption door does not exist
    assert _client().get("/auth/callback?code=x&state=y").status_code == 404


def test_no_session_denied_when_disabled(env) -> None:
    # legacy posture with no external login_url configured: 401 JSON, no redirect
    assert _client().get("/api/projects").status_code == 401


# --- /login initiates the handoff -------------------------------------------


def test_login_redirects_to_gate_with_client_id_and_state(env, monkeypatch) -> None:
    _enable(monkeypatch)
    res = _client().get("/login?next=/dashboard/tickets")
    assert res.status_code == 303
    loc = urlsplit(res.headers["location"])
    assert loc.netloc == "gate.diwata.domains" and loc.path == "/login"
    q = parse_qs(loc.query)
    assert q["client_id"] == ["assay"]
    assert q["redirect_uri"] == ["http://testserver/auth/callback"]
    assert q["state"]  # an opaque nonce
    # the round-trip is bound to a state cookie
    assert STATE_COOKIE_NAME in res.cookies


# --- the full round-trip: redeem → mint assay_session → authenticate ---------


def test_handoff_round_trip_mints_assay_session(env, monkeypatch) -> None:
    _enable(monkeypatch)
    _stub_exchange(monkeypatch, {"sub": _EMAIL, "email": _EMAIL})
    client = _client()

    begin = client.get("/login?next=/dashboard/tickets")
    nonce = parse_qs(urlsplit(begin.headers["location"]).query)["state"][0]

    # the gate lands the browser back on the callback with the code + our state
    cb = client.get(f"/auth/callback?code=one-time&state={nonce}")
    assert cb.status_code == 303
    assert cb.headers["location"] == "/dashboard/tickets"  # deep-link preserved
    assert ASSAY_COOKIE_NAME in cb.cookies

    # and that cookie authenticates a protected route (the client resends it)
    me = client.get("/api/projects")
    assert me.status_code == 200
    assert "projects" in me.json()


def test_callback_rejects_mismatched_state(env, monkeypatch) -> None:
    _enable(monkeypatch)
    _stub_exchange(monkeypatch, {"sub": _EMAIL, "email": _EMAIL})
    client = _client()
    client.get("/login?next=/dashboard")  # parks a state cookie
    # a different state than the one parked → bounce back to /login, no session
    res = client.get("/auth/callback?code=one-time&state=not-the-nonce")
    assert res.status_code == 303
    assert res.headers["location"] == "/login"
    assert ASSAY_COOKIE_NAME not in res.cookies


def test_callback_rejects_refused_code(env, monkeypatch) -> None:
    _enable(monkeypatch)

    async def _boom(config, code, redirect_uri):  # noqa: ANN001
        raise GateExchangeError("code is invalid, expired, or already used")

    monkeypatch.setattr(gate_sso, "exchange_code", _boom)
    client = _client()
    nonce = parse_qs(urlsplit(client.get("/login").headers["location"]).query)["state"][0]
    res = client.get(f"/auth/callback?code=bad&state={nonce}")
    assert res.status_code == 303
    assert res.headers["location"] == "/login"
    assert ASSAY_COOKIE_NAME not in res.cookies


# --- the middleware: page-load deny drives the handoff too -------------------


def test_page_load_deny_redirects_to_gate_when_enabled(env, monkeypatch) -> None:
    _enable(monkeypatch)
    res = _client().get("/dashboard")
    assert res.status_code == 303
    assert parse_qs(urlsplit(res.headers["location"]).query)["client_id"] == ["assay"]


# --- transition fallback: shared warden_session still authenticates ----------


def test_shared_cookie_still_authenticates_as_transition_fallback(env) -> None:
    """A live shared-cookie session (no assay_session) must not be dropped."""
    cfg = WardenConfig(secret=_SECRET)  # cookie_name defaults to warden_session
    token = issue_token(_EMAIL, cfg, extra={"email": _EMAIL})
    client = _client()
    client.cookies.set(SHARED_COOKIE_NAME, token)
    res = client.get("/api/projects")
    assert res.status_code == 200


# --- sign-out clears both cookies -------------------------------------------


def test_logout_clears_both_cookies(env) -> None:
    res = _client().get("/logout")
    blob = " ".join(res.headers.get_list("set-cookie"))
    assert ASSAY_COOKIE_NAME in blob
    assert SHARED_COOKIE_NAME in blob


def test_logout_bounces_to_gate_logout_not_login(env, monkeypatch) -> None:
    """With code-handoff on, logout must end the GATE's anchor session too.
    Redirecting to the gate's login page signs the user straight back in (the
    gate still holds a live session and immediately reissues a code) — the
    sign-out loop the founder hit on staging, 2026-08-11."""
    _enable(monkeypatch)
    res = _client().get("/logout")
    target = res.headers["location"]
    assert "/logout?next=" in target, target
    assert "/login" not in target.split("?")[0]
