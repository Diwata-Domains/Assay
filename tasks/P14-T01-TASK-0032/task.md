# Task: assay report --format html: single-file HTML report with inline base64 screenshots

## Metadata
- **ID:** TASK-0032
- **Status:** done
- **Phase:** Phase 14 — HTML Report
- **Backlog:** P14-T01
- **Packet Path:** tasks/P14-T01-TASK-0032/
- **Dependencies:** TASK-0022 (assay report table/json, Phase 11-T03)
- **Primary Adapter:** code_adapter
- **Secondary Adapters:** none

## Objective
Add `--format html` to the existing `assay report` command. The output is a single self-contained HTML file with all verification results rendered in a readable table, with screenshots embedded as base64-encoded inline images — no external assets required.

## Why This Task Exists
The current `assay report` only outputs a terminal table and JSON. An HTML report makes verification results shareable and readable without running Assay — useful for async review, client handoffs, and CI artifacts.

## Scope
- `src/assay/cli/main.py` — add `--format html` option to the `report` command (alongside existing `text` and `json`)
- `src/assay/formatter/` — add `html_formatter.py` (or equivalent module):
  - Accepts a list of verification packet dicts
  - Returns a single HTML string
  - HTML structure: page title, summary (total/pass/fail counts), results table (id, status, timestamp, test file, notes), inline `<img>` tags for each screenshot (base64-encoded PNG)
  - No external CSS or JS — all styling inline or in a `<style>` block
  - Readable in any browser without network access
- `src/assay/cli/main.py` — when `--format html`, write output to `assay-report.html` in the current directory (not stdout); print the output path on completion
- `tests/test_html_formatter.py` — unit tests: valid packets produce valid HTML, screenshot is embedded as base64, missing screenshot is handled gracefully (no `<img>` tag, not an error)

## Constraints
- Output must be a single self-contained file — no external dependencies
- Screenshots that don't exist on disk must be skipped gracefully, not crash
- Existing `--format text` and `--format json` behavior must not change
- Ruff + mypy must pass after implementation

## Escalation Conditions
- If existing packet format doesn't include a usable `screenshot_path` field, check `src/assay/schemas/assay_payload.schema.json` and adapt accordingly; flag if schema change is needed
