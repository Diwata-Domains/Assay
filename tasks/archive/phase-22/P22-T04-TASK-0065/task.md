# Task: Script library — built-in helpers (login, form fill, wait)

## Metadata
- **ID:** TASK-0065
- **Status:** pending
- **Phase:** Phase 22 — Multi-step Playwright Test Scripts
- **Backlog:** P22-T04
- **Packet Path:** tasks/P22-T04-TASK-0065/
- **Dependencies:** TASK-0062
- **Primary Adapter:** code

## Objective
Provide a built-in script helper library that script authors can import to use common patterns — login flows, form fills, element waits — without writing raw Playwright steps every time.

## Why This Task Exists
The raw step format from P22-T01 is sufficient but repetitive for common scenarios. A helper library reduces boilerplate for the most frequent verification patterns and makes scripts readable. This is especially important for the login-and-verify pattern that appears in almost every authenticated app.

## Scope
- Define the helper library as a small JS/TS module (`@assay/helpers` or bundled with the SDK) that the script runner makes available to scripts at runtime
- Built-in helpers:
  - `loginFlow({ url, usernameSelector, passwordSelector, username, password, submitSelector })` → navigates to login URL, fills credentials, clicks submit, waits for redirect
  - `fillForm({ fields: Array<{ selector, value }> })` → fills multiple form fields in sequence
  - `waitForText(selector, text)` → waits until the matched element contains the expected text
  - `waitForNetwork()` → waits for network idle (Playwright `networkidle`)
  - `screenshotStep(name)` → shorthand for a named screenshot step
- Each helper expands to the underlying step primitives defined in P22-T01 — no new execution logic
- Document the helper API in `docs/working/SCRIPT_HELPERS.md`
- Tests: each helper produces the correct step expansion

## Deliverable
Helper library available in scripts via import. `loginFlow`, `fillForm`, `waitForText`, `waitForNetwork`, `screenshotStep` implemented and documented. Tests passing.

## Constraints
- Helpers must expand to the same step primitives from P22-T01, not bypass the step runner
- The helper library must not require a build step — it should work when required/imported inside the Docker runner's Node.js environment
- Helpers are opt-in — scripts that use raw steps remain fully valid
