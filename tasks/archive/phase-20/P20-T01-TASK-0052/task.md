# Task: Admin credentials config (env vars + assay admin set-password)

## Metadata
- **ID:** TASK-0052
- **Status:** done
- **Phase:** P20-T01
- **Backlog:** P20-T01 — Admin credentials config (env vars + assay admin set-password)
- **Packet Path:** tasks/P20-T01-TASK-0052/
- **Dependencies:** none
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add admin credential management for the hosted dashboard. Read ASSAY_ADMIN_EMAIL, ASSAY_ADMIN_PASSWORD_HASH, and ASSAY_JWT_SECRET from environment variables. Add `assay admin set-password` CLI command that bcrypt-hashes a password and prints the hash ready to paste into .env. Add PyJWT and python-multipart to dependencies.

## Scope
- Add PyJWT and python-multipart to pyproject.toml dependencies
- Create src/assay/auth/ module with admin.py: read env vars, verify_password(), create_token(), verify_token()
- Add `admin_app = typer.Typer()` + `assay admin set-password` command in CLI
- Tests: test_admin_auth.py covering env var reading, password verify, token round-trip, missing env vars

## Constraints
- No credentials stored in assay.toml or SQLite — env vars only
- bcrypt already in dependencies
- JWT secret must be at least 32 chars — warn if shorter

## Escalation Conditions
- None
