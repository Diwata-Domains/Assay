# Task: Wire Warden into Assay — replace internal JWT auth

## Metadata
- **ID:** TASK-0076
- **Status:** in_progress
- **Phase:** Phase 27 — Warden Integration
- **Backlog:** P27-T01
- **Packet Path:** tasks/P27-T01-TASK-0076/
- **Dependencies:** TASK-0042 (packages/warden scaffold)
- **Primary Adapter:** code

## Objective
Replace Assay's internal JWT auth (`_AuthMiddleware`, `create_token`, `get_jwt_secret`)
with `packages/warden`. Cookie name migrates from `assay_session` to `warden_session`.
Env var migrates from `ASSAY_JWT_SECRET` to `WARDEN_SECRET`.

## Scope
- Update `WardenMiddleware` to support lazy config loading (config=None → WardenConfig.from_env() per request)
- Add `public_prefixes` to `WardenMiddleware` for `/status/` passthrough
- Add `warden` dep to Assay pyproject.toml
- `assay/auth/admin.py`: remove `create_token`, `get_jwt_secret`; keep password helpers
- `assay/ingest/app.py`: replace `_AuthMiddleware` + inline JWT with `WardenMiddleware`; update login/logout
- All affected tests: ASSAY_JWT_SECRET → WARDEN_SECRET, assay_session → warden_session, create_token → issue_token

## Deliverable
All 577 tests passing under new auth; ruff + mypy clean.
