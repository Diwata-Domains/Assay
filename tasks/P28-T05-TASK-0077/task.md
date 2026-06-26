# Task: Assay Ironvale Dashboard SPA

## Metadata
- **ID:** TASK-0077
- **Status:** done
- **Phase:** Phase 28 — Release v0.3.0 + Documentation Reconciliation
- **Backlog:** P28-T05 — Assay dashboard SPA
- **Packet Path:** tasks/P28-T05-TASK-0077/
- **Dependencies:** none
- **Primary Adapter:** none
- **Secondary Adapters:** none

> **ID note (collision):** the global archive max is TASK-0076, but `TASK-0077` was already
> minted by the closed Phase 29 packet (`tasks/P29-agent-surface-TASK-0077/`) and
> `docs/working/current_task.md` records the next free ID as TASK-0078. This packet
> deliberately reuses `TASK-0077` per the explicit work order for the dashboard SPA; the
> directory namespaces it as `P28-T05-TASK-0077` so it does not overwrite the P29 packet.
> Surfaced in `docs/working/tooling_notes.md` as a Grain friction point.

## Objective
Replace the server-rendered inline-HTML dashboard in `src/assay/ingest/app.py` (the `/`,
`/packet/{id}`, `/checks`, `/keys` routes built from f-string HTML) with a real React +
Ironvale single-page app served from `apps/assay-dashboard`, backed by a clean session-authed
JSON REST API on the existing FastAPI app. The SPA consumes the API contract below for packet
list, packet detail, baseline/diff image serving, and the approve / reject / set-baseline
review actions; the API reuses the existing store logic (`set_baseline`, `set_review_status`,
`get_baseline_for_url`, `list_packets`, `list_baselines`) and the same Warden session login
(NOT API-key, NOT a `public_prefixes` free pass). The built SPA mounts at `/dashboard` behind
the session middleware with an SPA index fallback.

## Why This Task Exists
The dashboard is the operator's visual-verification surface for v0.3.0 ("Visual Verification"
is the milestone theme — see `docs/working/current_focus.md`), but it is currently emitted as
hand-built f-string HTML inside the FastAPI handlers (`app.py` lines ~218–666): no component
reuse, no Ironvale design system, no client routing, and presentation is fused to data access.
The monorepo already ships a React + Ironvale app pattern (`apps/diwa-web`: React 19 + Vite 6 +
`@diwata/ironvale` + react-router + tanstack-query + vitest). Splitting the dashboard into an
API contract + an Ironvale SPA gives the dashboard the shared design system, makes the data
layer independently testable, and is the precondition for later dashboard work already seeded
in the backlog (multi-viewport side-by-side P28-T02/v0.4.0, error panel P30-T01, project filter
P31-T03).

## Scope
- New `apps/assay-dashboard` React + Ironvale SPA (Vite, mirrors `apps/diwa-web` toolchain):
  packet list (filter by outcome + task_id, paginated), packet detail (fields, candidate
  screenshot, baseline/diff slider + side-by-side), and review actions (approve / reject /
  set-baseline).
- New session-authed JSON REST API on the existing FastAPI app implementing the contract
  below, reusing the existing store functions — no new auth model, no `public_prefixes` entry.
- Image-serving endpoints (`candidate.png`, `baseline.png`, `diff.png`) returning
  `FileResponse` (404 when the artifact is absent), replacing today's inline base64 data URIs.
- SPA mount: `GET /dashboard` + `GET /dashboard/assets/*` serve the built static files under
  the session middleware, with SPA index fallback for client-side routes.
- Replace / retire the inline-HTML `/`, `/packet/{id}` rendering paths once the SPA is the
  dashboard (redirect `/` → `/dashboard`); keep `/login`, `/logout`, `/ingest`, `/health`,
  `/status/*`, `/mcp*`, `/baselines*`, and the API-key surfaces unchanged.

## Constraints
- **Auth:** session-auth only — reuse the existing Warden login (`/login`, the session cookie,
  `WardenMiddleware`). The `/api/*` and `/dashboard*` routes MUST be session-protected and MUST
  NOT be added to `public_paths` / `public_prefixes`, and MUST NOT accept `X-Assay-Key`. This is
  the same login as the existing HTML dashboard.
- **Reuse store logic:** the review POST reuses the existing `set_baseline` / `set_review_status`
  store calls exactly as `/packet/{id}/{approve,reject,set-baseline}` does today — no new review
  semantics.
- Trace commit format `type(scope): summary [TASK-0077]`; **no `Co-Authored-By` / AI
  attribution** (repo + product convention).
- Stage explicit paths only — never stage `.grain/`, `uv.lock`, `.venv/`, or `node_modules`.
- Canonical docs (`docs/canonical/`) require a change proposal before edits — avoid touching
  them; if `product_scope.md` needs the dashboard described, file a CP (do not edit directly).
- Python: ruff + mypy clean, pytest green (Docker-dependent tests excepted, as in TASK-0077/P29).
  SPA: `tsc --noEmit` clean and vitest green, mirroring `apps/diwa-web`.

## Escalation Conditions
- If the contract cannot be served session-only without weakening `WardenMiddleware` (e.g. a
  framework limitation forcing `/api/*` into `public_prefixes`) — stop and escalate; do not relax
  auth to ship.
- If retiring the inline-HTML `/packet/{id}` route would break an existing test or external
  link contract that cannot be redirected — escalate before deleting.
- If describing the shipped dashboard requires editing canonical `product_scope.md` — file a
  change proposal instead of editing (P28-T04 already owns that refresh).
