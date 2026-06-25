# Results — TASK-0077 Agent-Usable Verification Surface

**Status:** done (2026-06-25)

## What shipped

- **Shared engine** (`src/assay/api/service.py`): `run_verification`, `get_report`,
  `get_status` (via report), `list_runs`, `set_baseline`, `approve_baseline`,
  `reject_baseline`, `list_baselines`. Runner injectable (`runner_fn`) so tests drive the full
  loop without Docker.
- **Real MCP** (`src/assay/api/mcp.py`): rewritten to dispatch to the engine — no canned data.
  `/mcp/tools`, `/mcp/manifest`, `/mcp/call` all require `X-Assay-Key`. Removed `/mcp` from the
  Warden public-prefix free pass conceptually (route-level key auth replaces it).
- **Contract manifest** (`src/assay/contracts/manifest.py` + generated `tool_manifest.json`):
  8 tools + 9 endpoints + payload schema reference; served at `GET /mcp/manifest`; a drift-guard
  test asserts the on-disk JSON equals the module output.
- **CLI JSON + non-interactive init** (`src/assay/cli/main.py`): `--format json` on
  run/check/schedule list/key create/key list/baseline; `assay init --non-interactive|--yes`
  (flags or `ASSAY_ADMIN_EMAIL`/`ASSAY_ADMIN_PASSWORD`, no prompt/getpass) and `--format json`.
- **Headless baselines**: `assay baseline {list,set,approve,reject}` + API-key HTTP
  `GET /baselines`, `POST /baselines/{set,approve,reject}` (`src/assay/ingest/app.py`).
- **Docs**: README + AGENTS "Agent / programmatic access" sections; fixed `assay-sdk` →
  `@diwata-labs/assay-sdk` name drift.
- **Backlog**: relocated the stale `### Phase 29 — Alerts and Webhooks` appendix to
  `Deferred — Alerts and Webhooks` with `ALERT-T0x` IDs so the backlog has one Phase 29; marked
  P29-T01..T05 done; advanced current_focus + current_task.

## Tests

New: `tests/test_service.py`, `tests/test_mcp.py`, `tests/test_baseline_http.py`,
`tests/test_contracts.py`, `tests/test_agent_cli.py` (44 new tests). Full suite:
**599 passed, 16 failed** — the 16 failures are pre-existing and Docker-dependent
(`test_runner.py`, `test_e2e_run.py`, `test_compare_flag.py` invoke the real Docker runner;
this sandbox has no `docker` binary). No new tests touch Docker or a real browser. ruff + mypy
clean.

## Notes / remaining

- The pre-existing 16 Docker tests remain red in any Docker-less environment — unchanged by this
  task and out of scope (the task forbids real Docker in tests).
- `assay run` JSON mode intentionally skips the human `--compare` echo/grain-task side effects;
  the JSON object is the single machine-readable contract line.
