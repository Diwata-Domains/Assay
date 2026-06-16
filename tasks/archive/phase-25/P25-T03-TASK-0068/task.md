# Task: Header + security config checks

## Metadata
- **ID:** TASK-0068
- **Status:** done
- **Phase:** Phase 25 — Functional + Integration Checks
- **Backlog:** P25-T03
- **Packet Path:** tasks/P25-T03-TASK-0068/
- **Dependencies:** TASK-0067
- **Primary Adapter:** code

## Objective
Implement the `header` and `auth` check types. Header checks assert a response header is present/absent and optionally matches a value. Auth checks assert that a protected route returns 401/403 without credentials and 200 with a valid key.

## Why This Task Exists
CORS failures, missing security headers, and auth not being enforced are a class of bugs that only show up in headers — invisible to screenshot tests. This task makes them first-class assertions.

## Scope
- `src/assay/checks/header.py`: `run_header_check(config) -> CheckResult`
  - Assertions: `expect_header` (name), `expect_absent` (name), `expect_value` (str or regex)
- `src/assay/checks/auth.py`: `run_auth_check(config) -> CheckResult`
  - Asserts: unauthenticated request → 401 or 403; authenticated request (with `api_key` field) → 200
- Wire both types into `assay check` dispatcher
- Tests for each assertion variant

## Deliverable
`src/assay/checks/header.py` and `src/assay/checks/auth.py` implemented; wired into dispatcher; tests passing.

## Constraints
- Header name comparison must be case-insensitive (HTTP spec)
- Auth check `api_key` field reads from env var if value starts with `$` (e.g. `$ASSAY_API_KEY`)
