# Task: assay report reads from SQLite

## Metadata
- **ID:** TASK-0038
- **Status:** done
- **Phase:** P16-T03
- **Backlog:** P16-T03 — assay report reads from SQLite with filter and format preserved
- **Packet Path:** tasks/P16-T03-TASK-0038/
- **Dependencies:** TASK-0036, TASK-0037
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Update `assay report` to read packets from SQLite via `list_packets` instead of scanning JSON files on disk. All existing `--filter` and `--format` behaviour is preserved.

## Why This Task Exists
Phase 16 goal: all assay data flows through the SQLite store. The report command is the last consumer that still reads from disk JSON files.

## Scope
- Modify `report` command in `cli/main.py` to call `list_packets`
- Keep `--output` for backwards compatibility (used by html renderer for screenshots)
- Apply `--filter` on in-memory list after fetch
- Add `tests/test_report_sqlite.py`

## Constraints
- Graceful empty result when db doesn't exist (not an error)
- All existing report tests must stay green

## Escalation Conditions
- If the db schema changes required to support filter operators
