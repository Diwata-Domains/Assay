# Task: Auto-create Grain task on check failure

## Metadata
- **ID:** TASK-0073
- **Status:** done
- **Phase:** Phase 26 — Auto Grain Task on Failure
- **Backlog:** P26-T03
- **Packet Path:** tasks/P26-T03-TASK-0073/
- **Dependencies:** TASK-0071, TASK-0072
- **Primary Adapter:** code

## Objective
When `assay check` produces any failing CheckResult, call `create_check_failure_task()` for each failure if `grain.auto_create = true`. One Grain task packet per failing check.

## Why This Task Exists
Check failures need the same automatic tracking as visual regressions. A failed auth check or missing CORS header should appear in Grain without any manual step.

## Scope
- Wire `create_check_failure_task` (already in `grain/auto_task.py`) into `check_cmd` in `cli/main.py`
- After each failing result: extract failed assertions + error, call `create_check_failure_task`
- Print `grain task: <path>` for each written task
- Tests: task created on check failure, not created on pass, not created when auto_create=False

## Deliverable
`check_cmd` calls `create_check_failure_task` per failing result when auto_create=True; tests passing.

## Constraints
- Must not raise — failures in task writing are already silenced in `auto_task.py`
- One task per failing check (not one task for the whole run)
