# Deliverable Spec: TASK-0077 — Assay Ironvale Dashboard SPA

## Required Output

### New Files
- `apps/assay-dashboard/package.json` — `@diwata/assay-dashboard` (private), deps
  `@diwata/ironvale` + react 19 + react-router-dom 7 + `@tanstack/react-query` 5; scripts
  `dev`/`build`=`tsc --noEmit && vite build`/`typecheck`/`test` (mirrors `apps/diwa-web`).
- `apps/assay-dashboard/vite.config.ts` — `base: "/dashboard/"`, `/api` dev proxy, react plugin.
- `apps/assay-dashboard/tsconfig.json`, `apps/assay-dashboard/index.html`.
- `apps/assay-dashboard/src/main.tsx` — react-query client + router bootstrap.
- `apps/assay-dashboard/src/api/client.ts` — typed client for the contract below.
- `apps/assay-dashboard/src/routes/PacketList.tsx` — Ironvale table + outcome/task_id filter +
  pagination, reading `GET /api/packets`.
- `apps/assay-dashboard/src/routes/PacketDetail.tsx` — fields + candidate/baseline/diff images +
  Approve/Reject/Set-baseline actions, reading `GET /api/packets/{vid}` and the image routes.
- `apps/assay-dashboard/src/**/*.test.tsx` — vitest unit tests (API client + list/detail).
- `src/assay/ingest/api.py` (or an in-`app.py` router) — the session-authed REST + image +
  review endpoints.
- `tasks/P28-T05-TASK-0077/{task,context,plan,deliverable_spec,results}.md` (this packet).

### Modified Files
- `src/assay/ingest/app.py` — include the new API router; mount the built SPA at `/dashboard`
  + `/dashboard/assets/*` with SPA index fallback (session-protected, NOT in `public_*`);
  redirect `/` → `/dashboard`; retire/redirect the inline-HTML `dashboard()`/`packet_detail()`
  and their now-unused `_build_slider_html`/`_SLIDER_*` helpers.
- `tests/` — new backend tests for the API contract, image routes, review mutations, and
  session-auth enforcement (401/redirect without cookie, 200 with).
- `pnpm-workspace.yaml` / root `package.json` — only if `apps/*` is not already globbed by the
  workspace (verify; `apps/diwa-web` exists, so it likely already is).
- `docs/working/current_task.md` — set active task to TASK-0077 / this packet path.
- `docs/working/backlog.md` — add the **P28-T05 — Assay dashboard SPA** row under Phase 28.
- `docs/working/tooling_notes.md` — log the TASK-0077 ID-reuse collision.

## API Contract (authoritative — session-auth, same Warden login; NOT API-key; NOT public_prefixes)
- `GET /api/packets?limit=50&offset=0&outcome=&task_id=`
  → `{packets:[{verification_id, task_id, outcome, severity, review_status, url, verified_at,
  summary, has_diff, diff_pct}], total, limit, offset}`
- `GET /api/packets/{vid}`
  → `{verification_id, task_id, outcome, severity, review_status, url, summary, verified_at,
  diff_result, has_baseline, has_candidate, has_diff}`
- `GET /api/packets/{vid}/candidate.png` → `FileResponse` (candidate screenshot; 404 if none)
- `GET /api/packets/{vid}/baseline.png` → `FileResponse` (baseline for this packet's url; 404 if none)
- `GET /api/packets/{vid}/diff.png` → `FileResponse` (diff image; 404 if none)
- `POST /api/packets/{vid}/review` body `{action:"approve"|"reject"|"set-baseline"}`
  → `{verification_id, review_status}` (reuse existing `set_baseline`/`set_review_status` logic)
- SPA mount: `GET /dashboard` + `GET /dashboard/assets/*` → built `apps/assay-dashboard` static
  files, session-protected, SPA index fallback.

## Acceptance Checklist
- [ ] `apps/assay-dashboard` is a React + Ironvale SPA mirroring the `apps/diwa-web` toolchain
      (Vite 6, react 19, `@diwata/ironvale`, react-router-dom 7, tanstack-query 5, vitest).
- [ ] All seven contract endpoints implemented with the exact response shapes above.
- [ ] `/api/*` and `/dashboard*` are session-authenticated via the existing Warden login and are
      **absent** from `public_paths`/`public_prefixes`; they reject (401/redirect) without a
      session cookie and accept it (200) with one; they do NOT accept `X-Assay-Key`.
- [ ] Image routes return `FileResponse` PNG bytes and 404 when the artifact is missing.
- [ ] `POST /api/packets/{vid}/review` reuses the existing `set_baseline`/`set_review_status`
      store calls (approve → set-baseline + approved; reject → rejected; set-baseline → baseline)
      and returns the resulting `review_status`.
- [ ] Built SPA serves at `/dashboard`, deep links (`/dashboard/packet/{vid}`) resolve via the
      index fallback, and `/` redirects to `/dashboard`.
- [ ] Inline-HTML `dashboard()`/`packet_detail()` rendering is removed or redirected; `/login`,
      `/logout`, `/ingest`, `/health`, `/status/*`, `/mcp*`, `/baselines*` are unchanged.
- [ ] `docs/working/current_task.md`, `docs/working/backlog.md` (P28-T05 row), and
      `docs/working/tooling_notes.md` (ID collision) updated.
- [ ] All new tests passing (pytest + vitest).
- [ ] Full backend suite green (pre-existing Docker-only failures excepted); `ruff` + `mypy
      src/assay` clean; SPA `tsc --noEmit` + vitest green.
- [ ] review bundle complete in `results.md` and `handoff.md`.

## Not Required
- Porting `/checks` and `/keys` into the SPA — they may remain inline HTML this task (note if so).
- Project / multi-tenant filtering (P31), multi-viewport side-by-side (P28-T02/v0.4.0),
  error-panel/stack-trace view (P30-T01) — downstream phases that build on this split.
- Any change to the API-key agent surface (`/ingest`, `/baselines*`, `/mcp*`) or the runner/SDK.
- Editing canonical `docs/canonical/product_scope.md` — change-proposal only (P28-T04 owns it).
- Cutting the v0.3.0 release tag (P28-T01).
