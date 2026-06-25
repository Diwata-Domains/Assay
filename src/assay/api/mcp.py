# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Assay MCP server — engine-backed verification tools over HTTP.

This is the agent surface. Every tool dispatches to ``assay.api.service`` which drives the
real runner, store, and diff — there is no canned data. All ``/mcp/*`` routes require a valid
API key (``X-Assay-Key``); the contract an agent reads is ``assay.contracts``.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from assay.api import service
from assay.contracts.manifest import TOOLS, build_manifest
from assay.keys.store import verify_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["mcp"])


def _require_api_key(request: Request, x_assay_key: str | None) -> None:
    if not x_assay_key:
        raise HTTPException(status_code=401, detail="missing X-Assay-Key header")
    store = getattr(request.app.state, "key_store", "~/.assay/keys.json")
    if not verify_key(store, x_assay_key):
        raise HTTPException(status_code=401, detail="invalid or revoked API key")


def _store_db(request: Request) -> str:
    return getattr(request.app.state, "store_db", "~/.assay/store.db")


def _output_dir(request: Request) -> str:
    return getattr(request.app.state, "output_dir", "./assay-output")


@router.get("/tools")
async def list_tools(
    request: Request,
    x_assay_key: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_api_key(request, x_assay_key)
    return {"tools": TOOLS}


@router.get("/manifest")
async def manifest(
    request: Request,
    x_assay_key: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_api_key(request, x_assay_key)
    return build_manifest()


class CallRequest(BaseModel):
    tool: str
    input: dict[str, Any] = {}


@router.post("/call")
async def call_tool(
    request: Request,
    body: CallRequest,
    x_assay_key: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_api_key(request, x_assay_key)
    store_db = _store_db(request)
    output_dir = _output_dir(request)
    inp = body.input

    try:
        if body.tool == "run_verification":
            target = str(inp.get("target", "")).strip()
            if not target:
                return {"result": None, "error": "run_verification requires 'target'"}
            logger.info("MCP run_verification target=%s", target)
            result = service.run_verification(
                target,
                suite=str(inp.get("suite", "default")),
                output_dir=output_dir,
                store_db=store_db,
                task_id=inp.get("task_id"),
                verification_id=inp.get("verification_id"),
                no_docker=bool(inp.get("no_docker", False)),
                threshold=float(inp.get("threshold", 0.1)),
            )
            return {"result": result, "error": None}

        if body.tool == "get_report":
            vid = str(inp.get("verification_id", "")).strip()
            if not vid:
                return {"result": None, "error": "get_report requires 'verification_id'"}
            report = service.get_report(vid, store_db=store_db)
            if report is None:
                return {"result": None, "error": f"no report for {vid}"}
            return {"result": report, "error": None}

        if body.tool == "get_status":
            vid = str(inp.get("verification_id", "")).strip()
            if not vid:
                return {"result": None, "error": "get_status requires 'verification_id'"}
            report = service.get_report(vid, store_db=store_db)
            if report is None:
                return {
                    "result": {"verification_id": vid, "status": "pending"},
                    "error": None,
                }
            return {
                "result": {
                    "verification_id": vid,
                    "status": "complete",
                    "outcome": report.get("outcome", ""),
                    "regression": report.get("regression", False),
                },
                "error": None,
            }

        if body.tool == "list_runs":
            runs = service.list_runs(
                store_db=store_db,
                task_id=inp.get("task_id"),
                outcome=inp.get("outcome"),
            )
            return {"result": {"runs": runs}, "error": None}

        if body.tool == "list_baselines":
            baselines = service.list_baselines(store_db=store_db)
            return {"result": {"baselines": baselines}, "error": None}

        if body.tool in ("approve_baseline", "reject_baseline", "set_baseline"):
            vid = str(inp.get("verification_id", "")).strip()
            if not vid:
                return {"result": None, "error": f"{body.tool} requires 'verification_id'"}
            fn = getattr(service, body.tool)
            result = fn(vid, store_db=store_db)
            return {"result": result, "error": None}

    except service.ServiceError as exc:
        return {"result": None, "error": str(exc)}

    return {"result": None, "error": f"Unknown tool: {body.tool}"}
