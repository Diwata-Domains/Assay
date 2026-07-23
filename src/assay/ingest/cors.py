# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""DB-backed CORS: the allowed origin set is whatever is registered in project_origins.

Adding an origin in the dashboard immediately allows it — no redeploy. Results are cached
in-process keyed by (db_path, origin) and cleared via invalidate_origin_cache() on any
origin write, so the DB is not hit on every preflight and cached decisions never leak
across databases. allow_credentials stays False; the specific Origin is echoed (never '*').
"""

from __future__ import annotations

from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from assay.store.db import StoreError, get_project_for_origin

_ALLOW_METHODS = "POST, OPTIONS"
_ALLOW_HEADERS = "content-type, x-assay-key"
_MAX_AGE = "86400"

_cache: dict[tuple[str, str], bool] = {}


def invalidate_origin_cache() -> None:
    """Drop the cached origin decisions. Call after any project_origins write."""
    _cache.clear()


def origin_allowed(db_path: str, origin: str) -> bool:
    """True if ``origin`` is registered to some project in ``db_path``. Cached in-process."""
    resolved = str(Path(db_path).expanduser())
    key = (resolved, origin)
    if key in _cache:
        return _cache[key]
    try:
        allowed = get_project_for_origin(origin, db_path=Path(resolved)) is not None
    except StoreError:
        allowed = False
    _cache[key] = allowed
    return allowed


def _cors_headers(origin: str) -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": _ALLOW_METHODS,
        "Access-Control-Allow-Headers": _ALLOW_HEADERS,
        "Access-Control-Max-Age": _MAX_AGE,
        "Vary": "Origin",
    }


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """Per-request CORS whose allowed origins come from the project_origins table."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        origin = request.headers.get("origin")
        db_path = getattr(request.app.state, "store_db", "~/.assay/store.db")
        allowed = origin is not None and origin_allowed(db_path, origin)

        if request.method == "OPTIONS" and "access-control-request-method" in request.headers:
            if allowed and origin is not None:
                return Response(status_code=200, headers=_cors_headers(origin))
            return Response(status_code=400)

        response = await call_next(request)
        if allowed and origin is not None:
            for k, v in _cors_headers(origin).items():
                response.headers[k] = v
        return response
