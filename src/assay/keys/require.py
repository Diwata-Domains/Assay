# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Shared `X-Assay-Key` FastAPI dependency.

Extracted out of `assay.ingest.app` so machine-authed routers (e.g.
`assay.promotions.api`) can depend on it without importing `ingest.app` — which
would be circular, since `ingest.app` includes those routers.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, Request

from assay.keys.store import verify_key_project


def _require_api_key(request: Request, x_assay_key: str | None = Header(default=None)) -> str:
    if not x_assay_key:
        raise HTTPException(status_code=401, detail="missing X-Assay-Key header")
    store = request.app.state.key_store
    match = verify_key_project(store, x_assay_key)
    if match is None:
        raise HTTPException(status_code=401, detail="invalid or revoked API key")
    request.state.project_id = match.project_id
    return x_assay_key
