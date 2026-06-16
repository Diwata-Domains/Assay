# Task: SDK taskId passthrough to ingest payload

## Metadata
- **ID:** TASK-0027
- **Status:** done
- **Phase:** Phase 12 — Grain Task Tagging + assay submit
- **Backlog:** P12-T05
- **Packet Path:** tasks/P12-T05-TASK-0027/
- **Dependencies:** Phase 6 complete
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add optional `task_id` field to `IngestPayload` in `src/assay/ingest/app.py`. When present, set `packet["task_id"]` before writing. This allows browser SDK callers to tag their captures with a Grain task ID.

## Why This Task Exists
SDK captures need the same Grain task tagging capability as CLI runs. Without this, SDK packets always have `task_id: null`.

## Scope
- `task_id: str | None = None` on `IngestPayload`
- In `/ingest` handler: `if payload.task_id: packet["task_id"] = payload.task_id`

## Constraints
- Must remain optional — existing SDK callers without `taskId` must continue to work

## Escalation Conditions
- None
