# Context: TASK-0077 — Assay Ironvale Dashboard SPA

## Required Documents

### Runtime (always load)
- `products/assay/CLAUDE.md` — Grain workflow, commit rules, ruff/mypy/pytest gates, venv.
- root `CLAUDE.md` — Trace commit/branch format (`type(scope): summary [TASK-####]`), pnpm
  workspaces for TS packages, uv workspaces for Python.

### Canonical (load for this task)
- `docs/canonical/data_contracts.md` — packet schema + outcome/severity/review_status values
  that the `/api/packets*` responses surface (read-only; human approval required to edit).
- `src/assay/schemas/assay_payload.schema.json` — authoritative packet field shape the API
  serializes (verification_id, task_id, outcome, severity, url, summary, verified_at,
  diff_result, artifact_refs).

### Working (load if needed)
- `docs/working/current_focus.md` — Phase 28 is the active phase; v0.3.0 theme is "Visual
  Verification"; the dashboard is the visual surface.
- `docs/working/backlog.md` — Phase 28 task list (add the P28-T05 row); downstream dashboard
  work (P28-T02 viewport side-by-side, P30-T01 error panel, P31-T03 project filter) depends on
  this split.
- `docs/working/current_task.md` — set active task to TASK-0077 / this packet path.
- `docs/working/change_proposals.md` — CP-004 (`product_scope.md` dashboard refresh) lives in
  P28-T04; do not duplicate, do not edit canonical here.
- `docs/working/tooling_notes.md` — log the TASK-0077 ID-reuse collision (archive max is 0076,
  0077 already used by P29, current_task says next is 0078).

### Packet Files
- `tasks/P28-T05-TASK-0077/task.md`
- `tasks/P28-T05-TASK-0077/plan.md`
- `tasks/P28-T05-TASK-0077/deliverable_spec.md`

## Existing Code To Read / Reuse

### Backend (FastAPI)
- `src/assay/ingest/app.py` — the app to extend. Key existing pieces:
  - `WardenMiddleware` mount (lines ~28–32): `public_paths={/login,/logout,/ingest,/health,
    /docs,/openapi.json}`, `public_prefixes=("/status/","/mcp","/baselines")`. The new
    `/api/*` and `/dashboard*` routes are deliberately absent from both lists, so the
    middleware enforces the session cookie on them. **Do not add them.**
  - The inline dashboard handlers being replaced: `dashboard()` (`@app.get("/")`),
    `packet_detail()` (`@app.get("/packet/{verification_id}")`), and the review POSTs
    `set_packet_baseline` / `approve_packet` / `reject_packet` (the exact store calls the
    new `POST /api/packets/{vid}/review` must reuse).
  - `_attach_diff()` — shows how `diff_result` (`changed_pixels`/`total_pixels`/`diff_pct`/
    `diff_image_path`) and the `_diff.png` artifact are produced; `has_diff`/`diff_pct` in the
    list response derive from this.
  - `app.state.store_db` / `app.state.output_dir` — the SQLite path + artifact dir the API
    reads (overridable in tests).
- `src/assay/store/db.py` — reuse, do not reimplement:
  `list_packets(db_path, task_id=, outcome=)`, `list_baselines(db_path)` (returns
  `{url: verification_id}`), `get_baseline_for_url(url, db_path)`, `set_baseline(vid, db_path)`,
  `set_review_status(vid, status, db_path)`, `StoreError`.
- `src/assay/api/service.py` — engine layer added in P29 (`set_baseline`/`approve_baseline`/
  `reject_baseline`/`list_baselines`, `ServiceError`); the review endpoint may route through
  this for the approve/reject/set-baseline store logic to stay DRY with the API-key `/baselines*`
  surface.
- `src/assay/_vendor/warden/` — `WardenMiddleware`, `WardenConfig`, session cookie helpers
  (`set_session_cookie`/`clear_session_cookie`/`issue_token`) — the auth model to keep.

### Frontend (template to mirror)
- `apps/diwa-web/` — the canonical React 19 + Vite 6 + `@diwata/ironvale` + react-router-dom 7 +
  `@tanstack/react-query` 5 + vitest app. Copy its `package.json` scripts (`dev`/`build` =
  `tsc --noEmit && vite build`/`typecheck`/`test`), `tsconfig.json`, `vite.config.ts` shape.
- `packages/ironvale` (`@diwata/ironvale`) — the design-system components the SPA renders with
  (tables, badges, buttons, layout) instead of hand-rolled monospace HTML.

## Adapter Context
- **Primary Adapter:** none
- **Secondary Adapters:** none
- **Adapter Rationale:** n/a — internal product surface, no external integration adapter.

## Excluded Context
- `src/assay/api/mcp.py` and the API-key surfaces (`/ingest`, `/baselines*`, `/mcp*`) — those
  are the agent path (P29), session-orthogonal, and out of scope here.
- The browser/Playwright runner, Docker runner, SDK — the dashboard reads the store, it does
  not run verifications.
- Canonical `product_scope.md` edits — change-proposal only (P28-T04 owns the refresh).

## Context Sufficiency Note
`app.py` (existing dashboard + Warden mount + store calls), `store/db.py` (review/baseline
functions), and `apps/diwa-web` (React+Ironvale+Vite template) together fully specify both the
session-authed API and the SPA, so the contract can be implemented and reviewed without further
discovery.
