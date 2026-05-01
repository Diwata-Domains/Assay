# Task: assay report --export json

## Metadata
- **ID:** TASK-0039
- **Status:** done
- **Phase:** P16-T04
- **Backlog:** P16-T04 — assay report --export json: backwards-compatible dump
- **Packet Path:** tasks/P16-T04-TASK-0039/
- **Dependencies:** TASK-0038
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add `--export <path>` option to `assay report` that writes all matching packets as a JSON array to a file. Supports all existing `--filter` combinations. The file format must be compatible with the original `assay-*.json` on-disk layout.

## Why This Task Exists
Phase 16 goal: SQLite is the primary store. `--export` gives users a way to extract data back to JSON for interop with other tools or archival.

## Scope
- Add `--export` option to `assay report` (writes filtered packet list as JSON array to given path)
- Backwards-compatible: existing `--format json` stdout output unchanged
- Tests: `tests/test_report_export.py`

## Constraints
- `--export` must work with all `--format` modes
- No changes to existing `--format` behaviour

## Escalation Conditions
- None anticipated
