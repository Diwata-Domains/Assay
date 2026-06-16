# Task: Task deduplication

## Metadata
- **ID:** TASK-0074
- **Status:** done
- **Phase:** Phase 26 — Auto Grain Task on Failure
- **Backlog:** P26-T04
- **Packet Path:** tasks/P26-T04-TASK-0074/
- **Dependencies:** TASK-0072, TASK-0073
- **Primary Adapter:** code

## Objective
Before writing a Grain task for a check failure or visual regression, check whether an existing task file already covers the same check_id + target (or url + issue_type for regressions). Skip creation and return None if a duplicate is found.

## Why This Task Exists
Re-running `assay check` against a flaky endpoint would otherwise flood the Grain repo with identical task files. Deduplication keeps the task list signal-to-noise ratio high.

## Scope
- Add `_is_duplicate(dest_dir, key_fields)` helper in `grain/auto_task.py`
- `key_fields` for check failure: `{"issue_type": "check_failure", "check_id": ..., "target": ...}`
- `key_fields` for regression: `{"issue_type": "visual_regression", "url": ..., "diff_pct": ...}` — dedup on url only (not diff_pct)
- Scans `assay-*.json` in `dest_dir`, loads each, checks matching fields — returns True if duplicate found
- Tests: duplicate suppressed, first write succeeds, non-matching fields don't suppress

## Deliverable
`_is_duplicate` wired into both `create_regression_task` and `create_check_failure_task`; tests passing.

## Constraints
- Scan is best-effort — if a file can't be read, skip it (don't crash)
- Only dedup within the same `dest_dir` (grain repo output)
