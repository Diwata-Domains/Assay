# Plan: TASK-0077 — Assay Ironvale Dashboard SPA

## Approach
Split the dashboard into two independently testable halves on the existing FastAPI app: a
session-authed JSON REST API (`/api/packets*`) that reads the SQLite store and serves artifact
images as `FileResponse`, and a React + Ironvale SPA in `apps/assay-dashboard` (mirroring the
`apps/diwa-web` toolchain) mounted at `/dashboard` behind `WardenMiddleware`. The API reuses the
exact store calls the inline HTML handlers use today; the SPA consumes the contract via
`@tanstack/react-query` and react-router. Build the API first (test it directly), then the SPA
against it, then wire the static mount + SPA fallback, then retire the inline HTML.

---

## Step 1 — Session-authed REST API (`/api/packets*`)
Add the contract endpoints to `src/assay/ingest/app.py` (or a new `src/assay/ingest/api.py`
router included by `app.py`). All routes are session-protected by virtue of NOT being listed in
`public_paths`/`public_prefixes` — do not touch the middleware lists, do not accept
`X-Assay-Key`.

- `GET /api/packets?limit=50&offset=0&outcome=&task_id=` → `{packets:[...], total, limit,
  offset}`. Source from `store.db.list_packets(db_path, task_id=, outcome=)`; apply
  limit/offset; `total` is the unpaginated filtered count. Per-row fields: `verification_id,
  task_id, outcome, severity, review_status, url, verified_at, summary, has_diff, diff_pct`.
  Derive `review_status` from the packet, `has_diff` from `isinstance(diff_result, dict)`, and
  `diff_pct` from `diff_result["diff_pct"]` (else null/0). Mark the current baseline rows using
  `list_baselines(db_path)` if a `review_status`/badge needs it.
- `GET /api/packets/{vid}` → `{verification_id, task_id, outcome, severity, review_status, url,
  summary, verified_at, diff_result, has_baseline, has_candidate, has_diff}`. `has_candidate` =
  a non-`_diff` `.png` artifact exists on disk; `has_baseline` = `get_baseline_for_url(url)`
  resolves to a packet with a `.png` artifact on disk; `has_diff` = `diff_result` present AND
  its `diff_image_path` exists. 404 when the vid is unknown.
- Reuse the existing not-found / field-skip behavior conceptually (skip `raw`, `artifact_refs`
  in the structured fields; expose `diff_result` as structured JSON, not HTML).

Rationale: the SPA needs JSON, not HTML; keeping `total/limit/offset` lets the list paginate.

---

## Step 2 — Image-serving endpoints (`FileResponse`)
Add three image routes, session-protected, each returning `fastapi.responses.FileResponse`
(`media_type="image/png"`) or HTTP 404 when the artifact is absent:

- `GET /api/packets/{vid}/candidate.png` — the packet's own candidate screenshot (the non-`_diff`
  `.png` in `artifact_refs`, mirroring the `candidate_b64` selection in `packet_detail`).
- `GET /api/packets/{vid}/baseline.png` — the baseline screenshot for THIS packet's `url`
  (`get_baseline_for_url(packet.url)` → its non-`_diff` `.png`).
- `GET /api/packets/{vid}/diff.png` — the diff image (`diff_result["diff_image_path"]`).

This replaces the inline base64 data-URIs; the SPA references `<img src="/api/packets/{vid}/
candidate.png">` directly (cookie sent automatically, same-origin).

---

## Step 3 — Review action endpoint (`POST /api/packets/{vid}/review`)
`POST /api/packets/{vid}/review` body `{action: "approve" | "reject" | "set-baseline"}` →
`{verification_id, review_status}`. Reuse the EXACT store logic the inline POSTs use today:
- `approve` → `set_baseline(vid)` + `set_review_status(vid, "approved")` (as `approve_packet`).
- `reject` → `set_review_status(vid, "rejected")` (as `reject_packet`).
- `set-baseline` → `set_baseline(vid)` (as `set_packet_baseline`).
Prefer routing through `src/assay/api/service.py` (`approve_baseline`/`reject_baseline`/
`set_baseline`) so the session API and the API-key `/baselines*` surface share one code path.
Validate `action`; return the resulting `review_status`. Swallow `StoreError`/`ServiceError` to
a 404 for unknown vids (consistent with the existing handlers' tolerance).

---

## Step 4 — `apps/assay-dashboard` React + Ironvale SPA
Scaffold the app mirroring `apps/diwa-web`:
- `package.json` (`@diwata/assay-dashboard`, private, type module): deps `@diwata/ironvale`,
  `@diwata/aether` (if used by Ironvale), `react`/`react-dom` 19, `react-router-dom` 7,
  `@tanstack/react-query` 5; devDeps `@vitejs/plugin-react`, `vite` 6, `typescript` 5, `vitest`,
  `@types/react*`. Scripts: `dev`, `build`=`tsc --noEmit && vite build`, `typecheck`, `test`.
- `vite.config.ts` with `base: "/dashboard/"` and a dev proxy for `/api` → the FastAPI app;
  `tsconfig.json`, `index.html`.
- `src/`: a react-query client; an API client module typed to the contract; routes
  `/` (packet list: Ironvale table + outcome/task_id filter inputs + pagination) and
  `/packet/:vid` (detail: field list, candidate `<img>`, and a diff view — slider + side-by-side
  + diff-highlight tabs — driven off `has_baseline`/`has_candidate`/`has_diff`, plus
  Approve/Reject/Set-baseline buttons calling the review endpoint and invalidating queries).
- vitest unit tests for the API client + list/detail components (mock fetch), matching
  `apps/diwa-web`'s testing pattern.

Rationale: reuse the proven monorepo React stack and the Ironvale design system instead of
re-deriving styling; tanstack-query gives caching + invalidation for the review mutations.

---

## Step 5 — SPA static mount + index fallback
Serve the built SPA from FastAPI, session-protected:
- `GET /dashboard/assets/*` → the Vite-built `assets/` (StaticFiles or a `FileResponse` route).
- `GET /dashboard` and `GET /dashboard/{path:path}` → return the built `index.html` (SPA
  fallback so client routes like `/dashboard/packet/{vid}` deep-link correctly).
- Resolve the built-assets directory from a packaged path (e.g. `src/assay/dashboard_dist/` the
  Vite build outputs into) so `assay-kit` ships the SPA. Confirm absence of the build is handled
  gracefully (clear error / dev fallback), and that the mount stays OUTSIDE `public_*` lists.
- Redirect `GET /` → `/dashboard` so the old entry point still lands users on the dashboard.

---

## Step 6 — Retire inline HTML + reconcile docs
- Remove / redirect the inline-HTML `dashboard()` and `packet_detail()` rendering (and the
  `_build_slider_html`/`_SLIDER_*`/`_LOGIN_STYLE` etc. that only the inline pages used) once the
  SPA covers them; keep `/login`/`/logout` (HTML login is still the auth entry). Keep `/checks`
  and `/keys` as-is unless trivially portable (out of primary scope; note if deferred).
- Update `docs/working/current_task.md` (TASK-0077 active, this path), `docs/working/backlog.md`
  (add the P28-T05 "Assay dashboard SPA" row), and log the TASK-0077 ID-reuse collision in
  `docs/working/tooling_notes.md`. Do NOT edit canonical docs (CP only).

---

## Verification
- **Backend:** `.venv/bin/pytest` green (Docker tests excepted), `.venv/bin/ruff check .` and
  `.venv/bin/mypy src/assay` clean. New API tests assert: list pagination + outcome/task_id
  filters + per-row `has_diff`/`diff_pct`; detail `has_baseline`/`has_candidate`/`has_diff`
  flags; image routes return the bytes / 404; review approve/reject/set-baseline mutate the
  store exactly like the inline POSTs; and that `/api/*` + `/dashboard*` are 401/redirect
  without a session cookie (auth enforced, no public-prefix leak), but 200 with one.
- **Frontend:** `pnpm -F @diwata/assay-dashboard typecheck` clean, `pnpm -F
  @diwata/assay-dashboard test` green, `pnpm -F @diwata/assay-dashboard build` produces the
  `dist/` the FastAPI mount serves.
- **End-to-end (manual):** log in via `/login`, hit `/dashboard`, confirm the list renders from
  `/api/packets`, open a packet, see the candidate/baseline/diff images load, and approve a
  packet → `review_status` flips to `approved` and the badge updates.
