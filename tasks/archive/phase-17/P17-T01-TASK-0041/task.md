# Task: Dashboard route at `/` served by assay serve

## Metadata
- **ID:** TASK-0041
- **Status:** done
- **Phase:** P17-T01
- **Backlog:** P17-T01 — Dashboard route at `/` served by assay serve
- **Packet Path:** tasks/P17-T01-TASK-0041/
- **Dependencies:** TASK-0036
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add a `/` GET route to the FastAPI ingest app that serves a server-rendered HTML dashboard page. The page must load without any external network requests (fully self-contained). It reads packets from the SQLite store and renders a summary.

## Why This Task Exists
Phase 17 goal: the `assay serve` command exposes a web dashboard so operators can inspect packets in a browser without using the CLI.

## Scope
- Add `GET /` route to `ingest/app.py`
- Reads packets via `list_packets(app.state.store_db)`
- Returns `HTMLResponse` with server-rendered HTML (no external resources)
- Summary counts (total, pass, fail, inconclusive)
- Packet table (verification_id, outcome, severity, timestamp, summary)
- Reuse CSS style from html_formatter if possible, or inline minimal styles

## Constraints
- No JS frameworks, no CDN dependencies
- Must not break existing `/ingest` POST route or auth
- No template files — inline HTML in Python

## Escalation Conditions
- None anticipated
