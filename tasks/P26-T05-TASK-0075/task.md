# Task: Suggested remediation in task content

## Metadata
- **ID:** TASK-0075
- **Status:** done
- **Phase:** Phase 26 — Auto Grain Task on Failure
- **Backlog:** P26-T05
- **Packet Path:** tasks/P26-T05-TASK-0075/
- **Dependencies:** TASK-0072, TASK-0073, TASK-0074
- **Primary Adapter:** code

## Objective
Each auto-created Grain task includes a `remediation` field with a plain-language suggestion based on the failure type. Check failures use the check type + assertion name to pick a canned suggestion. Regression tasks get a generic visual diff suggestion.

## Why This Task Exists
A task that says "CORS header absent" is less useful than one that says "Add Access-Control-Allow-Origin to the response". Remediation turns a failure into an actionable directive.

## Scope
- Add `suggest_remediation(issue_type, check_type, assertion_name, target)` in `grain/auto_task.py`
- Rules:
  - `expect_header` / CORS: "Add the expected header to the server response for <target>"
  - `status_code` / HTTP: "Ensure the endpoint returns the expected status code; check service health at <target>"
  - `auth` / unauthenticated: "Verify the auth middleware is enforcing authentication on <target>"
  - `auth` / authenticated: "Ensure the API key is valid and the endpoint is accessible to authenticated clients"
  - `expect_text` / `expect_visible` / `expect_url`: "Update the page content or navigation to match the expected state"
  - regression: "Review recent changes affecting <url>; compare baseline vs current screenshot in Assay dashboard"
  - fallback: "Review the failure detail and fix the root cause"
- Field added to packet dict as `"remediation": <str>` in both create functions
- Tests: each rule returns expected substring, fallback fires on unknown type

## Deliverable
`suggest_remediation` in `auto_task.py`; `remediation` field in both packet types; tests passing.
