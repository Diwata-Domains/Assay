# Deliverable Spec — TASK-0077

## P29-T01 — Real engine-backed MCP + auth
- [x] `run_verification` drives the real runner and persists a real packet.
- [x] `get_report` reads the real store/diff (no canned JSON).
- [x] `/mcp/*` requires `X-Assay-Key`.

## P29-T02 — Full-loop contract + manifest
- [x] Tools: run, get_report, get_status (poll), list_runs (by task), baseline approve/reject/set/list.
- [x] One machine-readable manifest in `src/assay/contracts` (module + JSON), served at `/mcp/manifest`.

## P29-T03 — JSON + non-interactive init
- [x] `--format json` on run, check, schedule list, key create, key list (+ baseline, init).
- [x] `assay init` runs non-interactively (no prompt/getpass) for zero-touch agent setup.

## P29-T04 — Headless baselines
- [x] CLI `assay baseline {list,set,approve,reject}` + `--format json`.
- [x] API-key HTTP `GET /baselines`, `POST /baselines/{set,approve,reject}`.

## P29-T05 — Docs + SDK reconciliation
- [x] README + AGENTS "Agent / programmatic access" section.
- [x] Fixed `assay-sdk` → `@diwata-labs/assay-sdk` drift; documented SDK is NOT the agent path.

## Cross-cutting
- [x] Stale duplicate Phase 29 (Alerts/Webhooks) relocated — backlog has one Phase 29.
- [x] Phase 29 tasks marked done; current_focus advanced.
- [x] Tests extended; full suite green except pre-existing Docker-only failures; ruff + mypy clean.
