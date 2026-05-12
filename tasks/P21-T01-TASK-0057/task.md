# Task: Baseline capture — mark a packet as the approved baseline for a URL

## Metadata
- **ID:** TASK-0057
- **Status:** in_progress
- **Phase:** P21-T01
- **Backlog:** P21-T01 — Baseline capture: mark a packet as the approved baseline for a URL
- **Packet Path:** tasks/P21-T01-TASK-0057/
- **Dependencies:** P16 complete (SQLite store)
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add a baselines table to the SQLite store so any packet can be marked as the approved baseline for its URL. Add set_baseline/get_baseline functions to db.py. Add POST /packet/{id}/set-baseline route. Show baseline status in the dashboard list and packet detail view.

## Scope
- Add `baselines` table to db.py: url TEXT PRIMARY KEY, verification_id TEXT
- Add `set_baseline(verification_id, db_path)` — extracts URL from raw, upserts
- Add `get_baseline_for_url(url, db_path)` — returns packet dict or None
- Add `list_baselines(db_path)` — returns {url: verification_id} dict
- POST /packet/{id}/set-baseline — protected route, redirects to /packet/{id}
- Dashboard list: show "baseline" badge on the row that is the current baseline for its URL
- Packet detail: "Set as baseline" button
- Tests: test_baseline.py covering set, get, overwrite, list + route tests

## Constraints
- One baseline per URL — setting a new one overwrites the previous
- URL extracted from packet raw JSON field

## Escalation Conditions
- None
