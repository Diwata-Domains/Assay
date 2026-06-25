# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Machine-readable agent contract — the single source of truth for the agent surface.

This manifest describes every tool an agent can call to drive the verification loop
headlessly, the JSON Schema for each tool's input, and the HTTP endpoints that back them.
The MCP server (`/mcp/tools`, `/mcp/manifest`) serves this verbatim, so an agent never has
to guess the contract. Keep this in sync with `src/assay/api/service.py`.
"""

from __future__ import annotations

from typing import Any

CONTRACT_VERSION = "1"

_PROJECT_KEY_FIELD = {
    "type": "string",
    "description": "Identifier for the project / store namespace (informational).",
}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "run_verification",
        "description": (
            "Trigger a REAL visual-regression verification run against a target URL. Drives the"
            " Playwright runner, persists a result packet, and diffs against the URL's baseline"
            " when one exists. Returns the verification_id, outcome, packet_path, and diff."
        ),
        "http": {"method": "POST", "path": "/mcp/call", "tool": "run_verification"},
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "URL to verify (e.g. https://app.example.com).",
                },
                "project_key": _PROJECT_KEY_FIELD,
                "suite": {"type": "string", "description": "Suite name (metadata)."},
                "task_id": {
                    "type": "string",
                    "description": "Grain TASK-#### this run verifies. Optional.",
                },
                "verification_id": {
                    "type": "string",
                    "description": "Grain-issued VERIFY-XXXX-NNN ID. Generated if omitted.",
                },
                "no_docker": {
                    "type": "boolean",
                    "description": "Run Playwright directly via Node instead of Docker.",
                },
                "threshold": {
                    "type": "number",
                    "description": "Regression threshold as percent of changed pixels.",
                },
            },
            "required": ["target"],
        },
    },
    {
        "name": "get_report",
        "description": (
            "Fetch the structured report for a verification_id from the store: outcome,"
            " summary, diff stats, artifact paths, baseline/review status."
        ),
        "http": {"method": "POST", "path": "/mcp/call", "tool": "get_report"},
        "input_schema": {
            "type": "object",
            "properties": {
                "verification_id": {
                    "type": "string",
                    "description": "The verification_id returned by run_verification.",
                }
            },
            "required": ["verification_id"],
        },
    },
    {
        "name": "get_status",
        "description": (
            "Poll a verification_id for completion. Returns status=complete with the outcome"
            " once the packet is in the store, or status=pending if not found yet."
        ),
        "http": {"method": "POST", "path": "/mcp/call", "tool": "get_status"},
        "input_schema": {
            "type": "object",
            "properties": {
                "verification_id": {
                    "type": "string",
                    "description": "The verification_id to poll.",
                }
            },
            "required": ["verification_id"],
        },
    },
    {
        "name": "list_runs",
        "description": (
            "List run summaries from the store, optionally filtered by task_id or outcome."
            " Use this to enumerate every verification tied to a Grain task."
        ),
        "http": {"method": "POST", "path": "/mcp/call", "tool": "list_runs"},
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Filter by Grain TASK-####."},
                "outcome": {
                    "type": "string",
                    "enum": ["pass", "fail", "inconclusive"],
                    "description": "Filter by outcome.",
                },
            },
        },
    },
    {
        "name": "list_baselines",
        "description": "List every set baseline as {url, verification_id} pairs.",
        "http": {"method": "POST", "path": "/mcp/call", "tool": "list_baselines"},
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "approve_baseline",
        "description": (
            "Approve a packet: make it the baseline for its URL and mark review_status=approved."
            " The agent's equivalent of the dashboard Approve button."
        ),
        "http": {"method": "POST", "path": "/mcp/call", "tool": "approve_baseline"},
        "input_schema": {
            "type": "object",
            "properties": {
                "verification_id": {
                    "type": "string",
                    "description": "The packet to approve as the new baseline.",
                }
            },
            "required": ["verification_id"],
        },
    },
    {
        "name": "reject_baseline",
        "description": (
            "Reject a packet: mark review_status=rejected and keep the existing baseline."
        ),
        "http": {"method": "POST", "path": "/mcp/call", "tool": "reject_baseline"},
        "input_schema": {
            "type": "object",
            "properties": {
                "verification_id": {
                    "type": "string",
                    "description": "The packet to reject.",
                }
            },
            "required": ["verification_id"],
        },
    },
    {
        "name": "set_baseline",
        "description": "Make a packet the baseline for its URL without recording a review verdict.",
        "http": {"method": "POST", "path": "/mcp/call", "tool": "set_baseline"},
        "input_schema": {
            "type": "object",
            "properties": {
                "verification_id": {
                    "type": "string",
                    "description": "The packet to set as baseline.",
                }
            },
            "required": ["verification_id"],
        },
    },
]

ENDPOINTS: list[dict[str, Any]] = [
    {
        "method": "POST",
        "path": "/ingest",
        "auth": "X-Assay-Key",
        "description": "Submit a captured screenshot payload. JSON Schema: sdk_ingest.schema.json.",
        "schema": "sdk_ingest.schema.json",
    },
    {
        "method": "GET",
        "path": "/status/{verification_id}",
        "auth": "none",
        "description": "Poll a verification by id; returns complete + outcome or not_found.",
    },
    {
        "method": "GET",
        "path": "/mcp/tools",
        "auth": "X-Assay-Key",
        "description": "List the agent tools and their input schemas.",
    },
    {
        "method": "GET",
        "path": "/mcp/manifest",
        "auth": "X-Assay-Key",
        "description": "Full machine-readable agent contract (this manifest).",
    },
    {
        "method": "POST",
        "path": "/mcp/call",
        "auth": "X-Assay-Key",
        "description": "Invoke a tool by name with a JSON input object.",
    },
    {
        "method": "GET",
        "path": "/baselines",
        "auth": "X-Assay-Key",
        "description": "List set baselines as JSON.",
    },
    {
        "method": "POST",
        "path": "/baselines/set",
        "auth": "X-Assay-Key",
        "description": "Set a packet as baseline (body: {verification_id}).",
    },
    {
        "method": "POST",
        "path": "/baselines/approve",
        "auth": "X-Assay-Key",
        "description": "Approve a packet as baseline (body: {verification_id}).",
    },
    {
        "method": "POST",
        "path": "/baselines/reject",
        "auth": "X-Assay-Key",
        "description": "Reject a packet (body: {verification_id}).",
    },
]


def build_manifest() -> dict[str, Any]:
    """Return the full agent contract manifest."""
    return {
        "contract_version": CONTRACT_VERSION,
        "service": "assay",
        "description": (
            "Agent-usable verification surface for Assay. Agents drive the full loop via the CLI,"
            " POST /ingest (JSON Schema sdk_ingest.schema.json), or these MCP tools — NOT the"
            " browser SDK."
        ),
        "auth": {
            "header": "X-Assay-Key",
            "note": "All /mcp/* and /baselines* endpoints require a valid API key.",
        },
        "tools": TOOLS,
        "endpoints": ENDPOINTS,
        "payload_schema": "assay_payload.schema.json",
    }
