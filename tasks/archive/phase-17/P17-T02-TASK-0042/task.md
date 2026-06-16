# Task: Packet list view with screenshot indicator

## Metadata
- **ID:** TASK-0042
- **Status:** done
- **Phase:** P17-T02
- **Backlog:** P17-T02 — Packet list view: table with outcome, severity, screenshot, timestamp
- **Packet Path:** tasks/P17-T02-TASK-0042/
- **Dependencies:** TASK-0041
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Enhance the `GET /` dashboard table to include a screenshot indicator column (yes/no based on artifact_refs containing a .png path), and linkify rows to a future detail view at `/packet/<verification_id>`.

## Why This Task Exists
Phase 17 goal: the dashboard is a useful inspection tool. The packet list needs the screenshot column (mirrors `assay report` CLI) and clickable rows for drill-down navigation.

## Scope
- Add screenshot indicator column to dashboard table (yes/no)
- Make verification_id link to `/packet/<verification_id>`
- Tests: update `test_dashboard.py` to cover screenshot column

## Constraints
- `/packet/<verification_id>` doesn't need to exist yet — just the link href
- No external resources

## Escalation Conditions
- None anticipated
