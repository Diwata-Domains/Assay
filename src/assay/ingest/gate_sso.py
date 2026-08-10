# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Assay's own session cookie + the code-handoff seam (Phase 0a).

Until now Assay had no session of its own: the browser cookie was the gate-minted
Warden cookie on the shared ``.diwata.domains`` scope, which WardenMiddleware read
directly. That only works because gate.diwata.domains and assay.diwata.domains
share a registrable domain. The moment the gate moves to diwata.id that cookie can
no longer be read here — so Assay switches to CODE-HANDOFF (one_login_spec.md §4,
already how Diwa/Conclave/Apex sign in): the browser is sent to the gate with
Assay's client_id + registered callback, the gate returns a one-time code on that
callback, and Assay redeems it server-side (per-client GATE_CLIENT_SECRET_ASSAY)
to mint its OWN host-scoped ``assay_session`` cookie.

Assay differs from Conclave/Apex in WHERE the redirect is kicked off. Assay is a
server-rendered app (FastAPI serves the legacy HTML pages AND the /dashboard SPA)
whose middleware already REDIRECTS unauthenticated browsers to the gate — the SPA
never runs a login screen, it just bounces 401s to the server's /login. So the
handoff is driven entirely server-side: the middleware deny and the /login route
redirect to the gate with client_id+redirect_uri+state, and GET /auth/callback
redeems the code. No SPA change, no browser-held secret.

Unlike Conclave, Assay has no keeper/user table — a gate-verified identity IS the
authorization for the operator console (like Apex/Daemon). So the exchange
redeems the code, mints the session cookie carrying the gate-shaped payload
(sub=email + email claim), and that's it — no JIT provisioning.

``assay_session`` is a DISTINCT cookie name from the shared ``warden_session`` on
purpose: during the transition a browser may carry BOTH (the gate still sets the
shared one for other apps), and one host would otherwise send two cookies of the
same name — an ambiguous read. A distinct name keeps them from colliding. The
middleware verifies ``assay_session`` first and falls back to the legacy shared
``warden_session`` only as a transition bridge, so no live production session is
dropped on rollout. Both verify with WARDEN_SECRET. Once the gate leaves
``.diwata.domains`` the shared cookie simply never arrives and the fallback yields
nothing — the bridge self-obsoletes with no code change.

Everything here is inert until ASSAY_GATE_SSO is on: with the flag off the
``assay_session`` cookie is never minted, only the shared cookie is ever present,
and the middleware is byte-identical to the WardenMiddleware it replaces.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import replace
from typing import Any
from urllib.parse import quote, urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.types import ASGIApp

from assay._vendor.warden import (
    GateClientConfig,
    GateExchangeError,
    TokenExpired,
    TokenInvalid,
    WardenConfig,
    WardenConfigError,
    begin_login_url,
    clear_session_cookie,
    exchange_code,
    issue_token,
    set_session_cookie,
    verify_token,
)

# Assay's own session cookie — host-scoped, never on the shared domain.
ASSAY_COOKIE_NAME = "assay_session"
# The legacy shared gate cookie, read only as a transition fallback.
SHARED_COOKIE_NAME = "warden_session"
# Short-lived cookie binding the handoff round-trip to the browser that started
# it (the server-side analog of the SPA's sessionStorage state — CSRF binding).
STATE_COOKIE_NAME = "assay_gate_state"
_STATE_TTL_SECONDS = 600

# Assay's registered client id at the gate (gate clients.json). Passed explicitly
# (never GATE_CLIENT_ID env) because the operator stack shares one .env across
# services, so the generic GATE_CLIENT_ID may belong to another product — see
# GateClientConfig.from_env's per-client secret lookup (GATE_CLIENT_SECRET_ASSAY).
GATE_CLIENT_ID = "assay"


class HandoffError(Exception):
    """The code-handoff round-trip could not be completed (bad/expired state,
    refused code, or a misconfigured client). The caller bounces back to /login."""


def gate_sso_enabled() -> bool:
    """Is code-handoff on? Read straight from the environment (Assay's config is
    TOML-based; this flag is an operator/SOPS env var like APEX_GATE_SSO). Fails
    CLOSED — an unconfigured service must not open a new auth door."""
    return os.environ.get("ASSAY_GATE_SSO", "").strip().lower() in ("1", "true", "yes", "on")


def gate_client_config() -> GateClientConfig | None:
    """Assay's registered gate-client connection, or None if the companion env
    (GATE_PUBLIC_ORIGIN + GATE_CLIENT_SECRET_ASSAY) is incomplete."""
    try:
        return GateClientConfig.from_env(client_id=GATE_CLIENT_ID)
    except WardenConfigError:
        return None


def assay_session_config() -> WardenConfig:
    """The config for Assay's OWN ``assay_session`` cookie.

    Same signing secret / TTL / Secure flag / SameSite as the environment's
    Warden config, but a distinct cookie NAME and a forced-empty cookie DOMAIN so
    the cookie is host-scoped to Assay's own host — never the shared
    ``.diwata.domains`` scope (that would recreate the very coupling code-handoff
    removes)."""
    base = WardenConfig.from_env()
    return replace(base, cookie_name=ASSAY_COOKIE_NAME, cookie_domain="")


def _state_config() -> WardenConfig:
    """Config for the short-lived, host-scoped handoff-state cookie."""
    base = WardenConfig.from_env()
    return replace(
        base, cookie_name=STATE_COOKIE_NAME, cookie_domain="", ttl_seconds=_STATE_TTL_SECONDS
    )


def callback_uri(request: Request) -> str:
    """This host's registered gate callback, EXACTLY matching clients.json.

    Derived from the forwarded host/proto (Assay runs behind the operator nginx,
    which terminates TLS and sets Host + X-Forwarded-Proto=https), so both the
    begin leg and the exchange leg compute the identical string — the gate
    matches redirect_uri byte-for-byte."""
    proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip() or request.url.scheme
    host = request.headers.get("host", "").strip() or request.url.netloc
    return f"{proto}://{host}/auth/callback"


def _safe_next(raw: str | None) -> str:
    """Reduce an arbitrary ``next`` (the SPA sends a full href; the middleware a
    path) to a same-site PATH. Guards against open redirects — the result always
    starts with ``/`` or falls back to the dashboard."""
    if not raw:
        return "/dashboard"
    parts = urlsplit(raw)
    dest = parts.path + (f"?{parts.query}" if parts.query else "")
    return dest if dest.startswith("/") else "/dashboard"


def begin_handoff(request: Request, next_url: str | None) -> RedirectResponse | None:
    """Send the browser to the gate for code-handoff, parking a state cookie.

    Returns None when the client env is incomplete (a half-configured door stays
    shut — the caller falls back to the legacy shared-cookie bounce so users are
    never locked out)."""
    config = gate_client_config()
    if config is None:
        return None
    nonce = secrets.token_urlsafe(16)
    state_cfg = _state_config()
    token = issue_token(nonce, state_cfg, extra={"next": _safe_next(next_url)})
    resp = RedirectResponse(
        begin_login_url(config, callback_uri(request), nonce), status_code=303
    )
    set_session_cookie(resp, token, state_cfg)
    return resp


def _read_state(request: Request) -> tuple[str, str] | None:
    """The parked (nonce, next) from the state cookie, or None if absent/invalid."""
    token = request.cookies.get(STATE_COOKIE_NAME, "")
    if not token:
        return None
    try:
        payload = verify_token(token, _state_config())
    except (TokenExpired, TokenInvalid):
        return None
    return str(payload.get("sub", "")), str(payload.get("next", ""))


async def complete_handoff(request: Request) -> RedirectResponse:
    """Redeem the gate's one-time code and mint Assay's OWN ``assay_session``.

    The gate landed the browser at /auth/callback with ?code=&state=. Validate
    the state against the parked cookie (single-use CSRF binding), redeem the
    code server-side via Warden (with GATE_CLIENT_SECRET_ASSAY — no secret ever
    rides the browser), and set the session cookie carrying the gate-shaped
    payload (sub=email + email claim) the middleware reads. Raises HandoffError
    on any failure. On success, redirects to where the visitor was headed."""
    config = gate_client_config()
    if config is None:
        raise HandoffError("gate client not configured")
    code = request.query_params.get("code", "")
    returned_state = request.query_params.get("state", "")
    parked = _read_state(request)
    if not code or not returned_state or parked is None or parked[0] != returned_state:
        raise HandoffError("stale or mismatched sign-in state")
    try:
        identity = await exchange_code(config, code, callback_uri(request))
    except GateExchangeError as exc:
        raise HandoffError("exchange refused") from exc
    email = str(identity.get("email") or identity.get("sub") or "").strip().lower()
    if not email:
        raise HandoffError("gate returned no identity")
    dest = parked[1] if parked[1].startswith("/") else "/dashboard"
    resp = RedirectResponse(dest, status_code=303)
    cfg = assay_session_config()
    set_session_cookie(resp, issue_token(email, cfg, extra={"email": email}), cfg)
    clear_session_cookie(resp, _state_config())  # single-use
    return resp


class AssaySessionMiddleware(BaseHTTPMiddleware):
    """Enforce a session on protected paths, reading Assay's OWN ``assay_session``
    cookie first and the legacy shared ``warden_session`` only as a transition
    fallback.

    Mirrors the vendored WardenMiddleware's posture (public paths/prefixes, deny
    everything else without a valid session), with two adaptations:
    - the two-cookie read (own cookie first) — the transition bridge that lets a
      single deploy carry both live shared-cookie and fresh code-handoff sessions;
    - the deny path: when code-handoff is on it redirects to the gate with
      client_id+redirect_uri+state (server-driven handoff); otherwise it is the
      EXACT legacy behaviour (redirect to ``login_url`` with ?next=, or 401 JSON
      when no login_url is configured).
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        public_paths: frozenset[str] = frozenset({"/health"}),
        public_prefixes: tuple[str, ...] = (),
        protected_prefixes: tuple[str, ...] = ("/",),
        login_url: str | None = None,
    ) -> None:
        super().__init__(app)
        self._public_paths = public_paths
        self._public_prefixes = public_prefixes
        self._protected_prefixes = protected_prefixes
        self._login_url = login_url

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path

        if path in self._public_paths:
            return await call_next(request)  # type: ignore[no-any-return]
        if self._public_prefixes and any(path.startswith(p) for p in self._public_prefixes):
            return await call_next(request)  # type: ignore[no-any-return]
        if not any(path.startswith(p) for p in self._protected_prefixes):
            return await call_next(request)  # type: ignore[no-any-return]

        payload = self._resolve(request)
        if payload is None:
            return self._deny(request)
        request.state.warden_user = payload
        return await call_next(request)  # type: ignore[no-any-return]

    def _resolve(self, request: Request) -> dict[str, Any] | None:
        """The verified session payload from either cookie, or None.

        assay_session (Assay's own) wins; warden_session (shared, legacy) is the
        transition fallback. A present-but-invalid cookie of one name never blocks
        trying the other. ``WardenConfig.from_env()`` is deferred until a cookie
        is actually present — a cookieless request denies without needing
        WARDEN_SECRET set (matches WardenMiddleware's laziness)."""
        cfg: WardenConfig | None = None
        for name in (ASSAY_COOKIE_NAME, SHARED_COOKIE_NAME):
            token = request.cookies.get(name, "")
            if not token:
                continue
            if cfg is None:
                cfg = WardenConfig.from_env()
            try:
                return verify_token(token, cfg)
            except (TokenExpired, TokenInvalid):
                continue
        return None

    def _deny(self, request: Request) -> Response:
        if gate_sso_enabled():
            handoff = begin_handoff(request, request.url.path)
            if handoff is not None:
                return handoff
        if self._login_url:
            next_param = quote(str(request.url), safe="")
            sep = "&" if "?" in self._login_url else "?"
            return RedirectResponse(f"{self._login_url}{sep}next={next_param}", status_code=303)
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
