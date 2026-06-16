# Task: Packet detail view at /packet/<verification_id>

## Metadata
- **ID:** TASK-0043
- **Status:** done
- **Phase:** P17-T03
- **Backlog:** P17-T03 — Packet detail view: full fields + inline screenshot
- **Packet Path:** tasks/P17-T03-TASK-0043/
- **Dependencies:** TASK-0041, TASK-0042
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add `GET /packet/{verification_id}` route that renders a full-detail page for a single packet: all fields in a definition list, and if artifact_refs contains a `.png` path that exists on disk, an inline `<img>` tag (base64-encoded).

## Why This Task Exists
Phase 17 goal: clickable rows in the dashboard lead to a detail view so operators can inspect individual verification results and screenshots.

## Scope
- `GET /packet/{verification_id}` route
- Fetches packet by ID from SQLite via `list_packets(outcome=None, task_id=None)` filtered by verification_id, or a direct lookup helper
- Renders: all packet fields, inline base64 screenshot if png exists on disk
- Returns 404 HTML page if not found
- Tests: `tests/test_packet_detail.py`

## Constraints
- No external resources
- Screenshot inline only if the file exists on disk (silently omit if missing)

## Escalation Conditions
- None anticipated
