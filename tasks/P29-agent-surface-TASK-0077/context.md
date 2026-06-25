# Context — TASK-0077

## Starting state
- `src/assay/api/mcp.py` was a STUB: `run_verification` returned `{job_id, status:queued}` and
  `get_report` returned `{status:no_baseline}` — canned data, the biggest agent-correctness risk.
- `/mcp` was a Warden public prefix (unauthenticated).
- Baseline approve/reject lived only in the dashboard (`/packet/{id}/approve|reject`).
- The CLI had `--format json` only on `report`; `assay init` used `typer.prompt` + `getpass`.
- README referenced `assay-sdk` while the package is `@diwata-labs/assay-sdk`.
- `docs/working/backlog.md` had a stale `### Phase 29 — Alerts and Webhooks` appendix colliding
  with the authoritative `## Phase 29 — Agent-Usable Verification Surface`.

## Key existing pieces reused
- `assay.runner.runner` / `assay.runner.artifacts` — real runner + artifact collection.
- `assay.formatter.formatter.format_packet`, `assay.formatter.writer.write_packet`.
- `assay.store.db` — packets, baselines, review_status, list_packets(task_id/outcome).
- `assay.diff.engine.diff_images` — pixel diff.
- `assay.keys.store.verify_key` — API-key auth (same pattern as `/ingest`).

## Constraints honored
- No real browser/Docker in tests (runner injected as a callable).
- Trace commit format, no AI attribution, explicit path staging.
