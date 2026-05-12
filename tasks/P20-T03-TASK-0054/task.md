# Task: Auth middleware protecting dashboard routes

## Metadata
- **ID:** TASK-0054
- **Status:** done
- **Phase:** P20-T03
- **Backlog:** P20-T03 — Auth middleware protecting dashboard routes
- **Packet Path:** tasks/P20-T03-TASK-0054/
- **Dependencies:** TASK-0053
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add middleware to the FastAPI app that checks the assay_session JWT cookie on every request to protected routes (GET /, GET /packet/{id}, GET /keys). Unauthenticated requests redirect to /login. Public routes (POST /ingest, GET /status/{id}, GET /login, POST /login, GET /logout) remain accessible without a session.

## Scope
- Starlette middleware that reads the assay_session cookie, verifies JWT, allows or redirects
- Protected: GET /, GET /packet/*, GET /keys (and sub-paths)
- Public: /login, /logout, /ingest, /status/*
- If ASSAY_ADMIN_* env vars are not set, protected routes return 503 with a setup message
- Tests: test_auth_middleware.py covering protected redirect, public pass-through, valid session access, expired/invalid token redirect

## Constraints
- Middleware must not break the ingest endpoint (SDK callers must never be redirected)
- Use Starlette middleware (not FastAPI dependency injection) so it covers all routes uniformly

## Escalation Conditions
- None
