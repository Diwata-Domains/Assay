# Task: Login page + JWT cookie session

## Metadata
- **ID:** TASK-0053
- **Status:** done
- **Phase:** P20-T02
- **Backlog:** P20-T02 — Login page + JWT cookie session (GET /login, POST /login, GET /logout)
- **Packet Path:** tasks/P20-T02-TASK-0053/
- **Dependencies:** TASK-0052
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add login/logout routes to the FastAPI app. GET /login serves an HTML form matching the dashboard dark theme. POST /login validates email+password against env vars, sets an HTTP-only JWT cookie on success, redirects to / on failure. GET /logout clears the cookie and redirects to /login.

## Scope
- GET /login — HTML login form (dark theme, consistent with dashboard)
- POST /login — form handler: verify email+password, set assay_session cookie (HTTP-only, SameSite=lax), redirect to /
- GET /logout — delete cookie, redirect to /login
- Tests: test_login.py covering login success, wrong password, wrong email, logout

## Constraints
- Cookie must be HTTP-only to prevent JS access
- On failed login: re-render the form with an error message, do not redirect
- No rate limiting yet (Phase 26 concern)

## Escalation Conditions
- None
