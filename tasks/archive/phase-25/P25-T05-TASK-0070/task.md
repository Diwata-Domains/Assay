# Task: Check results in dashboard + report output

## Metadata
- **ID:** TASK-0070
- **Status:** done
- **Phase:** Phase 25 — Functional + Integration Checks
- **Backlog:** P25-T05
- **Packet Path:** tasks/P25-T05-TASK-0070/
- **Dependencies:** TASK-0066, TASK-0067, TASK-0068, TASK-0069
- **Primary Adapter:** code

## Objective
Surface check results in the dashboard and `assay report`. Dashboard gets a dedicated "Checks" tab showing id, type, target, pass/fail, assertion detail, and timestamp. `assay report` includes check results alongside visual packets. JSON output includes a `checks` array with a structured result per check.

## Why This Task Exists
Results that aren't visible are results that don't get acted on. This closes Phase 25 by making check outcomes discoverable from both the CLI and the web UI.

## Scope
- Dashboard: new `/checks` route and tab in the navbar; table view with check id, type, target, status, detail, timestamp
- `assay report`: include check results in table output and JSON export (`--format json`)
- JSON report: top-level `checks` array parallel to existing packets array
- Tests: report output includes checks, dashboard route returns 200

## Deliverable
Dashboard checks tab live; `assay report` prints check results; JSON export includes `checks` array; tests passing.

## Constraints
- Dashboard checks tab must load independently of visual packets (separate query)
- `assay report` without `--checks` flag still shows only visual packets (backwards compatible)
- `assay report --checks` or `assay report --all` includes check results
