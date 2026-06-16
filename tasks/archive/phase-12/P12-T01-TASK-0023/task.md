# Task: `assay run --task-id` flag; populate task_id in packet

## Metadata
- **ID:** TASK-0023
- **Status:** done
- **Phase:** Phase 12 — Grain Task Tagging + assay submit
- **Backlog:** P12-T01
- **Packet Path:** tasks/P12-T01-TASK-0023/
- **Dependencies:** Phase 4 complete
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add `--task-id` option to `assay run`. When provided, pass it to `format_packet(bundle, task_id=...)` so the output packet's `task_id` field is set to the given Grain task ID.

## Why This Task Exists
The payload schema has a `task_id` field for linking verifications to Grain task packets. Without this flag there was no way to set it from the CLI.

## Scope
- `--task-id` option in `assay run` command
- Pass to `format_packet()` as `task_id` keyword argument
- `task_id=None` when flag not provided (standalone mode)

## Constraints
- `task_id` must remain optional per CP-001 option B

## Escalation Conditions
- None
