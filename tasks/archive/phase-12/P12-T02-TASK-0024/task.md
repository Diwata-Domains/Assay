# Task: Grain auto-detection: read current_task.md / GRAIN_TASK_ID env

## Metadata
- **ID:** TASK-0024
- **Status:** done
- **Phase:** Phase 12 — Grain Task Tagging + assay submit
- **Backlog:** P12-T02
- **Packet Path:** tasks/P12-T02-TASK-0024/
- **Dependencies:** TASK-0023
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Implement `detect_task_id()` in `src/assay/grain/detect.py`. Resolution order: (1) `GRAIN_TASK_ID` env var, (2) parse `TASK-\d+` from `docs/working/current_task.md` relative to project_root or cwd. Integrate into `assay run` so task_id is auto-populated without requiring `--task-id`.

## Why This Task Exists
In a Grain project, the active task is always tracked in `current_task.md`. Auto-detection means zero manual wiring for Grain users.

## Scope
- `src/assay/grain/detect.py`: `detect_task_id(project_root=None) -> str | None`
- Reads `GRAIN_TASK_ID` env first
- Falls back to regex search in `docs/working/current_task.md`
- Integrated in `assay run`: `effective_task_id = task_id or detect_task_id(...)`

## Constraints
- Must not raise on missing file or unreadable content — return None silently
- `GRAIN_TASK_ID` takes precedence over file

## Escalation Conditions
- None
