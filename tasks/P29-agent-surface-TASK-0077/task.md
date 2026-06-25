# Task: Agent-Usable Verification Surface

## Metadata
- **ID:** TASK-0077
- **Status:** in_progress
- **Phase:** Phase 29 — Agent-Usable Verification Surface
- **Backlog:** P29-T01..P29-T05
- **Packet Path:** tasks/P29-agent-surface-TASK-0077/
- **Dependencies:** none
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Make Assay fully familiar-drivable (agent-usable, agent-agnostic) so an agent can drive the
full verification loop headlessly with no browser. Replace the MCP stub with a real
engine-backed server, expand the tool contract to full-loop coverage with a machine-readable
manifest, add JSON output and non-interactive init across the CLI, expose headless baseline
management over CLI + API-key HTTP, and document the agent path (CLI / POST /ingest / MCP —
NOT the browser SDK).

## Why This Task Exists
The CLI is the most complete surface, but the MCP server returned canned data — it misled
agents into believing they triggered a real run (the biggest agent-correctness risk). Baseline
approval was dashboard-only. The browser SDK is not the agent path.

## Scope
- P29-T01: real engine-backed MCP (`run_verification`/`get_report`) + `/mcp/*` auth.
- P29-T02: full-loop tool contract (submit, status/poll, report, list-by-task, baseline
  approve/reject) + one machine-readable manifest in `src/assay/contracts`.
- P29-T03: `--format json` on run/check/schedule/key; non-interactive `assay init`.
- P29-T04: headless baseline approve/reject/set + JSON list via CLI + API-key HTTP.
- P29-T05: agent-access docs in README/AGENTS; fix `assay-sdk` name drift; dedup stale Phase 29.

## Constraints
- No real browser/Docker in tests — mock the runner/store.
- Trace commit format `type(scope): summary`; no AI attribution.
- Stage explicit paths only; never stage `.grain/` caches.

## Escalation Conditions
- Canonical `docs/canonical/` edits would require a change proposal (avoided here).
