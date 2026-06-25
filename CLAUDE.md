# Claude Code Instructions — Assay

## Project Overview

Assay is an independent verification layer for software projects. It runs Playwright tests in Docker, captures browser screenshots via a TypeScript SDK, formats results into Grain-compatible task packets, and exposes a FastAPI ingest endpoint with API key auth.

- **PyPI package:** `assay-kit` (`uv tool install assay-kit`)
- **CLI entrypoint:** `assay` (via `src/assay/cli/main.py`)
- **Python source:** `src/assay/`
- **TypeScript SDK:** `sdk/`
- **Docker runner:** `runner/`
- **Tests:** `tests/` (pytest) + `sdk/` (vitest)

---

## Grain Workflow

This project uses **Grain** for task and phase management. Grain is the operator's own workflow tool. Before starting any task:

1. Create a task packet directory: `tasks/P{phase}-T{n}-TASK-{id}/` containing `task.md`, `context.md`, `plan.md`, `deliverable_spec.md`, `results.md`
2. Set the task status to `ready` in its `task.md`
3. Update `docs/working/current_task.md` with the task ID and path
4. Update `docs/working/backlog.md` to reflect the current status

**Never skip task packet creation.** Even in resumed sessions where work feels ready to begin, create the packet first. This was logged as a known friction point (`docs/working/tooling_notes.md`, 2026-04-22).

Task packets are numbered sequentially. **Do not trust a hardcoded counter** — derive the
next ID from the archive each time:

```bash
ls -d tasks/archive/phase-*/*/ | grep -oE 'TASK-[0-9]+' | sort -t- -k2 -n | tail -1
```

As of the 2026-06-25 reconciliation the archive max is **TASK-0076**, so the next task is
**TASK-0077**. (Historical note: IDs restart once — Phases 1–5 use TASK-0001…0026, then
Phase 6 restarts at TASK-0001 and runs monotonically to TASK-0076 at Phase 27. Use the
global max from the command above, not the last phase's local numbering.)

Templates are in `templates/` — use them for new packets.

---

## Commit Rules

- **Never add `Co-Authored-By` lines** to commit messages — not for Claude, not for any tool
- Commit messages should be concise and lowercase (e.g. `phase 12: Grain task tagging`)
- Do not commit `.DS_Store`, `assay-output/`, or any secrets

---

## Code Conventions

- **Formatter/linter:** `ruff` — run `.venv/bin/ruff check .` before committing
- **Type checker:** `mypy` — run `.venv/bin/mypy src/assay` before committing
- **Tests:** `pytest` — run `.venv/bin/pytest` — must stay green at all times
- **Python version:** 3.11+
- **No comments** unless the WHY is non-obvious — never describe what the code does
- Use `cast(list[dict[str, object]], ...)` pattern for mypy when `list(object)` fails — do not use `# type: ignore[arg-type]`
- Lazy-import APScheduler inside function bodies — patch at `apscheduler.schedulers.blocking.BlockingScheduler` in tests

## Virtual Environment

```bash
source .venv/bin/activate
# or call directly:
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy src/assay
```

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/working/current_focus.md` | Current phase and active priorities |
| `docs/working/backlog.md` | All phases and task status |
| `docs/working/current_task.md` | Active task ID — update when switching tasks |
| `docs/working/change_proposals.md` | CPs requiring human approval before applying |
| `docs/working/tooling_notes.md` | Grain workflow friction log |
| `docs/canonical/data_contracts.md` | Authoritative schema + CLI spec — human approval required for edits |
| `src/assay/schemas/assay_payload.schema.json` | JSON schema for output packets |

---

## Canonical Docs

`docs/canonical/` requires **human approval** before any direct edits. File a change proposal in `docs/working/change_proposals.md` first.

---

## Current Phase

See `docs/working/current_focus.md` for the authoritative active phase and closed-phase
ledger. As of 2026-06-25: **Phase 28 — Release v0.3.0 + Documentation Reconciliation**.
v0.1.0 and v0.2.0 are released; v0.3.0 is implemented (Phases 17–27) and pending release.
