# Task: HTTP assertion engine

## Metadata
- **ID:** TASK-0067
- **Status:** done
- **Phase:** Phase 25 — Functional + Integration Checks
- **Backlog:** P25-T02
- **Packet Path:** tasks/P25-T02-TASK-0067/
- **Dependencies:** TASK-0066
- **Primary Adapter:** code

## Objective
Implement the `http` check type: assert status code, response time threshold, body contains string, and body matches JSON path. Each assertion failure produces a structured result with expected vs actual. Exit 1 if any assertion fails.

## Why This Task Exists
HTTP assertions are the most common check type — catching 500s, slow endpoints, and broken JSON contracts without needing a browser. Feeds into the `assay check` dispatcher from T01.

## Scope
- `src/assay/checks/http.py`: `run_http_check(config) -> CheckResult`
- Assertions: `expect_status` (int), `max_response_ms` (int), `body_contains` (str), `body_json_path` (str + expected value)
- Each assertion produces a named pass/fail with actual vs expected in the result
- Wire into `assay check` dispatcher (type = "http")
- Tests: status assertion, timing assertion, body contains, JSON path, multi-assertion result

## Deliverable
`src/assay/checks/http.py` implemented and wired; tests passing; `assay check` runs `http` type checks end-to-end.

## Constraints
- Use `httpx` (already a dep) for requests — no new HTTP client
- Timeouts must be configurable per check; default 10s
- JSON path syntax: simple dot-notation (`response.status`) — no JSONPath library required
