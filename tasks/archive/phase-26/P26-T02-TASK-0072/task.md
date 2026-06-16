# Task: Auto-create Grain task on visual regression

## Metadata
- **ID:** TASK-0072
- **Status:** done
- **Phase:** Phase 26 — Auto Grain Task on Failure
- **Backlog:** P26-T02
- **Packet Path:** tasks/P26-T02-TASK-0072/
- **Dependencies:** TASK-0071
- **Primary Adapter:** code

## Objective
When `assay run --compare` detects a regression (diff_pct > threshold), automatically create a Grain task packet in the configured repo if `grain.auto_create = true`. The task is written as a JSON file in `<grain.repo>/<grain.output_path>/` with a structured title, description, URL, diff stats, and timestamp.

## Why This Task Exists
The whole point of auto-detection is that failures get tracked without manual intervention. This is the first hook — visual regressions go straight into Grain.

## Scope
- New module `src/assay/grain/auto_task.py` with `create_regression_task(url, diff_result, config)` 
- Task packet fields: verification_id (new UUID), task_id (None), issue_type="visual_regression", severity="error", outcome="fail", summary="Visual regression: <url>", verified_at, artifact_refs (diff image path if present)
- Written to `<grain.repo>/<grain.output_path>/assay-<uuid>.json` via `write_packet`
- Call site: `_do_compare()` in `cli/main.py` — after detecting regression, call `create_regression_task` if `config.grain.auto_create`
- Tests: task file written on regression, not written when auto_create=False, not written when no regression

## Deliverable
`grain/auto_task.py` with regression task writer; wired into `_do_compare`; tests passing.

## Constraints
- Must not raise on write failure — log warning, continue
- Only fires when `config.grain.auto_create is True` and `config.grain.repo` is set
- Does not depend on T03/T04/T05
