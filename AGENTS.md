# Agent Instructions — Assay

## Project Overview

Assay is an independent verification layer for software projects. It runs Playwright tests in Docker, captures browser screenshots via a TypeScript SDK, formats results into Grain-compatible task packets, and exposes a FastAPI ingest endpoint with API key auth.

- **PyPI package:** `assay-kit` (`uv tool install assay-kit`)
- **CLI entrypoint:** `assay` (via `src/assay/cli/main.py`)
- **Python source:** `src/assay/`
- **TypeScript SDK:** `sdk/`
- **Docker runner:** `runner/`
- **Tests:** `tests/` (pytest) + `sdk/` (vitest)

---

## Before Starting Any Task

1. Create a task packet directory: `tasks/P{phase}-T{n}-TASK-{id}/`
2. Populate `task.md`, `context.md`, `plan.md`, `deliverable_spec.md`, `results.md` from templates in `templates/`
3. Set task status to `ready` in `task.md`
4. Update `docs/working/current_task.md` with the task ID and path
5. Update `docs/working/backlog.md` to reflect `in_progress`

Do not trust a hardcoded counter — derive the next task ID from the archive each time:

```bash
ls -d tasks/archive/phase-*/*/ | grep -oE 'TASK-[0-9]+' | sort -t- -k2 -n | tail -1
```

As of the 2026-06-25 reconciliation the archive max is **TASK-0076**, so the next packet is
**TASK-0077**. (IDs restart once: Phases 1–5 use 0001…0026, then Phase 6 restarts at 0001
and runs monotonically to 0076 — use the global max from the command above.)

Never skip this step — even in resumed sessions or when the work seems straightforward.

---

## Commit Rules

- No `Co-Authored-By` lines of any kind
- Lowercase, concise commit messages
- Do not commit `.DS_Store`, `assay-output/`, or secrets

---

## Code Quality — Must Pass Before Every Commit

```bash
.venv/bin/ruff check .        # linting
.venv/bin/mypy src/assay      # type checking
.venv/bin/pytest              # 250 tests must pass
```

- Python 3.11+, strict mypy
- No inline comments unless the WHY is non-obvious
- Use `cast(list[dict[str, object]], ...)` over `# type: ignore[arg-type]` for mypy list issues
- Lazy-import APScheduler inside function bodies; patch `apscheduler.schedulers.blocking.BlockingScheduler` in tests

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/working/current_focus.md` | Current phase and priorities |
| `docs/working/backlog.md` | All phases and task statuses |
| `docs/working/current_task.md` | Active task — keep updated |
| `docs/working/change_proposals.md` | Proposals pending human approval |
| `docs/working/tooling_notes.md` | Workflow friction log |
| `docs/canonical/data_contracts.md` | Authoritative schema + CLI spec |
| `src/assay/schemas/assay_payload.schema.json` | Output packet JSON schema |

---

## Canonical Docs Policy

`docs/canonical/` requires **human approval** before edits. File a change proposal in `docs/working/change_proposals.md` first.

---

## Output Packet Schema

Required fields: `verification_id`, `task_id`, `issue_type`, `severity`, `outcome`, `summary`
Optional fields: `artifact_refs`, `followup_candidates`, `verified_at`

`task_id` is optional for standalone runs; required for Grain-integrated runs.

---

## Agent / programmatic access

A familiar (agent) drives Assay headlessly through **three surfaces** — the CLI, `POST /ingest`,
and the MCP server. **Do NOT use the browser SDK** (`@diwata-labs/assay-sdk`): its `capture()`
reads the live DOM and throws outside a browser, so it is the human/in-app path, not the agent path.

The machine-readable contract (tools + JSON Schemas + endpoints) is the source of truth:
- on disk: `src/assay/contracts/tool_manifest.json` (built from `src/assay/contracts/manifest.py`)
- over HTTP: `GET /mcp/manifest`

Surfaces:

1. **CLI** — most complete. `--format json` on `run`, `check`, `schedule list`, `key create`,
   `key list`, `baseline {list,set,approve,reject}`, and `init`. `assay init --non-interactive`
   (alias `--yes`) never prompts/`getpass` — pass `--admin-email`/`--admin-password` or set
   `ASSAY_ADMIN_EMAIL`/`ASSAY_ADMIN_PASSWORD`.
2. **`POST /ingest`** — `X-Assay-Key` auth; body per `src/assay/schemas/sdk_ingest.schema.json`.
3. **MCP** — `GET /mcp/tools`, `GET /mcp/manifest`, `POST /mcp/call` (all `X-Assay-Key`-authed,
   engine-backed — no canned data). Tools: `run_verification`, `get_report`, `get_status`,
   `list_runs`, `list_baselines`, `approve_baseline`, `reject_baseline`, `set_baseline`.

Headless baselines are also exposed over API-key HTTP: `GET /baselines`,
`POST /baselines/{set,approve,reject}`.

The shared engine behind all three surfaces is `src/assay/api/service.py` (CLI/HTTP/MCP all
call it, so behaviour is identical). See README "Agent / programmatic access" for examples.

---

## Current State

See `docs/working/current_focus.md` for the authoritative active phase. As of 2026-06-25:
**Phase 28 — Release v0.3.0 + Documentation Reconciliation**. v0.1.0 and v0.2.0 are released
to PyPI as `assay-kit`; v0.3.0 is implemented (Phases 17–27) and pending release. Task state
is in `docs/working/backlog.md`.
