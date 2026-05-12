# Task: Key management UI (list, create, revoke from browser)

## Metadata
- **ID:** TASK-0055
- **Status:** done
- **Phase:** P20-T04
- **Backlog:** P20-T04 — Key management UI (list, create, revoke from browser)
- **Packet Path:** tasks/P20-T04-TASK-0055/
- **Dependencies:** TASK-0054
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add /keys routes so the admin can manage API keys from the browser without SSH. GET /keys lists active keys and shows a create form. POST /keys creates a key and shows the raw value once. POST /keys/{id}/revoke revokes a key. All routes are protected by the auth middleware.

## Scope
- GET /keys — HTML page: list active keys (label, created_at), create form with label input
- POST /keys — create key, redirect back to /keys with the raw key shown once in a highlight box
- POST /keys/{id}/revoke — revoke key, redirect to /keys
- Dark theme consistent with dashboard
- Tests: test_keys_ui.py covering list, create shows key once, revoke, revoke unknown id

## Constraints
- Raw key value shown exactly once after creation — not stored, not retrievable again
- Use POST for revoke (HTML forms only support GET/POST)

## Escalation Conditions
- None
