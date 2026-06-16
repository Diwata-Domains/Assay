# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Assay MCP server — exposes visual regression verification tools over HTTP."""
import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mcp", tags=["mcp"])

_TOOLS = [
    {
        "name": "run_verification",
        "description": (
            "Trigger a visual regression verification run for a project."
            " Returns a job ID that can be polled via get_report."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_key": {
                    "type": "string",
                    "description": "The project key to run verification on.",
                },
                "branch": {
                    "type": "string",
                    "description": "Optional branch name for comparison.",
                },
            },
            "required": ["project_key"],
        },
    },
    {
        "name": "get_report",
        "description": (
            "Fetch the latest verification report for a project."
            " Returns pass/fail status and a list of differing screenshots."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_key": {
                    "type": "string",
                    "description": "The project key to fetch the report for.",
                },
            },
            "required": ["project_key"],
        },
    },
]


@router.get("/tools")
async def list_tools() -> dict:
    return {"tools": _TOOLS}


class CallRequest(BaseModel):
    tool: str
    input: dict[str, Any] = {}


@router.post("/call")
async def call_tool(body: CallRequest) -> dict:
    if body.tool == "run_verification":
        project_key = body.input.get("project_key", "")
        branch = body.input.get("branch", "main")
        logger.info("Verification run requested: project=%s branch=%s", project_key, branch)
        # Phase 4 stub — full implementation in Assay Phase 22
        return {
            "result": {
                "job_id": f"assay-{project_key}-pending",
                "status": "queued",
                "message": "Verification queued. Fetch report once complete.",
            },
            "error": None,
        }

    if body.tool == "get_report":
        project_key = body.input.get("project_key", "")
        # Phase 4 stub — real implementation reads from assay store
        return {
            "result": {
                "project_key": project_key,
                "status": "no_baseline",
                "message": "No baseline found. Run a verification first.",
                "diffs": [],
            },
            "error": None,
        }

    return {"result": None, "error": f"Unknown tool: {body.tool}"}
