# Task: GET /status/{verification_id} endpoint

## Metadata
- **ID:** TASK-0046
- **Status:** done
- **Phase:** P18-T03
- **Backlog:** P18-T03 — GET /status/{verification_id} endpoint
- **Packet Path:** tasks/P18-T03-TASK-0046/
- **Dependencies:** TASK-0036, TASK-0045
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add `GET /status/{verification_id}` JSON endpoint to the ingest app. Returns `{status, outcome, verified_at}` for the given verification_id from the SQLite store, or 404 if not found.

## Why This Task Exists
Grain's verify flow may poll for completion. Assay needs a stable HTTP endpoint to answer status queries without requiring file system access.

## Scope
- `GET /status/{verification_id}` returns JSON
- Looks up by verification_id in SQLite via list_packets
- Returns: `{"status": "complete"|"pending"|"not_found", "outcome": ..., "verified_at": ...}`
- 404 JSON response if not found
- Tests: `tests/test_status_endpoint.py`

## Constraints
- No auth required (status is non-sensitive)
- Must not break existing routes

## Escalation Conditions
- None
