# Task: Implement `assay report` command

## Metadata
- **ID:** TASK-0022
- **Status:** done
- **Phase:** Phase 11 — Screenshot Persistence + assay report
- **Backlog:** P11-T03
- **Packet Path:** tasks/P11-T03-TASK-0022/
- **Dependencies:** Phase 4 complete
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Replace the `assay report` stub with a working command that reads all `assay-*.json` packets from the output directory and renders a summary table. Support `--format json` for machine-readable output and `--filter key=val` for quick filtering.

## Why This Task Exists
`assay report` was a required command per the CLI spec but was a stub (exit 1). Phase 11 exit criterion: results are readable without opening JSON.

## Scope
- Text table: verification_id, outcome, severity, screenshot (yes/no), verified_at, summary
- `--format json`: emit the packet list as JSON array
- `--filter outcome=fail`: filter packets by field=value
- Error if output directory does not exist

## Constraints
- Must read `assay-*.json` glob, not arbitrary filenames
- Malformed packet files should be skipped silently, not crash the command

## Escalation Conditions
- None
