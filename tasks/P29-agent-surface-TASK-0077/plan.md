# Plan — TASK-0077 Agent-Usable Verification Surface

1. Add a shared engine service layer (`src/assay/api/service.py`) that the CLI, HTTP, and MCP
   all call: `run_verification`, `get_report`, `list_runs`, `set_baseline`, `approve_baseline`,
   `reject_baseline`, `list_baselines`. Store-backed; runner injectable for testability.
2. Rewrite `src/assay/api/mcp.py` to call the service, expose the full tool set, and
   authenticate via `X-Assay-Key` (removing `/mcp` from public prefixes).
3. Publish a machine-readable manifest (`src/assay/contracts/manifest.py` +
   `src/assay/contracts/tool_manifest.json`) and serve it at `GET /mcp/manifest`.
4. CLI: `--format json` on `run`/`check`/`schedule list`/`key list`/`key create`; non-interactive
   flags on `assay init` (no prompt/getpass).
5. CLI `assay baseline` subcommands (set/approve/reject/list) + API-key HTTP endpoints
   (`/baselines`, `/baselines/set`, `/baselines/approve`, `/baselines/reject`).
6. Docs: Agent/programmatic access section in README + AGENTS; fix `assay-sdk` → `@diwata-labs/assay-sdk`.
7. Backlog: remove stale duplicate Phase 29 appendix; mark P29 tasks done; advance current_focus.
8. Tests throughout; keep full suite green (excluding pre-existing Docker-dependent failures).
