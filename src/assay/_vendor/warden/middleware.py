"""Starlette/FastAPI middleware for Warden session enforcement."""

from __future__ import annotations

from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.types import ASGIApp

from .config import WardenConfig
from .exceptions import TokenExpired, TokenInvalid
from .tokens import verify_token


class WardenMiddleware(BaseHTTPMiddleware):
    """Enforce Warden session on protected paths.

    Reads the session cookie set by Warden, verifies the JWT, and either
    attaches the decoded payload to ``request.state.warden_user`` or redirects
    to the login URL.

    Args:
        app: The ASGI application to wrap.
        config: WardenConfig with signing secret and cookie settings. When None,
            ``WardenConfig.from_env()`` is called on each request — useful when
            the secret is provided via env vars that may not be set at import time.
        protected_prefixes: URL path prefixes that require authentication.
        public_paths: Exact paths that are always public (login, health, etc.).
        public_prefixes: Path prefixes that are always public (e.g. "/status/").
        login_url: Where to redirect unauthenticated requests. Set to None to
            return 401 JSON instead of redirecting (useful for APIs).
    """

    def __init__(
        self,
        app: ASGIApp,
        config: WardenConfig | None = None,
        protected_prefixes: tuple[str, ...] = ("/",),
        public_paths: frozenset[str] = frozenset({"/login", "/health"}),
        public_prefixes: tuple[str, ...] = (),
        login_url: str | None = "/login",
        cookie_name: str = "warden_session",
    ) -> None:
        super().__init__(app)
        self._config = config
        self._protected_prefixes = protected_prefixes
        self._public_paths = public_paths
        self._public_prefixes = public_prefixes
        self._login_url = login_url
        # Use config.cookie_name when a static config is provided, otherwise use the parameter.
        # This lets the middleware redirect unauthenticated requests without requiring
        # WARDEN_SECRET to be set (from_env() is only called when a token exists).
        self._cookie_name = config.cookie_name if config is not None else cookie_name

    def _get_config(self) -> WardenConfig:
        return self._config if self._config is not None else WardenConfig.from_env()

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path

        if path in self._public_paths:
            return await call_next(request)  # type: ignore[no-any-return]

        if self._public_prefixes and any(path.startswith(p) for p in self._public_prefixes):
            return await call_next(request)  # type: ignore[no-any-return]

        if not any(path.startswith(p) for p in self._protected_prefixes):
            return await call_next(request)  # type: ignore[no-any-return]

        token = request.cookies.get(self._cookie_name, "")
        if not token:
            return self._deny(request)

        cfg = self._get_config()
        try:
            payload = verify_token(token, cfg)
            request.state.warden_user = payload
        except (TokenExpired, TokenInvalid):
            response = self._deny(request)
            if isinstance(response, RedirectResponse):
                response.delete_cookie(self._cookie_name)
            return response

        return await call_next(request)  # type: ignore[no-any-return]

    def _deny(self, request: Request) -> Response:
        if self._login_url:
            return RedirectResponse(url=self._login_url, status_code=303)
        return JSONResponse({"detail": "not authenticated"}, status_code=401)
