# Results: TASK-0077 — Assay Ironvale Dashboard SPA

## Packet State
- **Current Task Status:** ready (packet opened; implementation not yet started)
- **Review Readiness:** not ready — execution pending
- **Recommended Next Status:** in_progress

## Files Changed
_None yet — this packet is `ready`. Implementation will populate this section. Planned surface:_
- `apps/assay-dashboard/**` — new React + Ironvale SPA (Vite, mirrors `apps/diwa-web`).
- `src/assay/ingest/api.py` (or router in `app.py`) — session-authed REST + image + review API.
- `src/assay/ingest/app.py` — include router, mount SPA at `/dashboard`, redirect `/`, retire
  inline-HTML dashboard/packet-detail rendering.
- `tests/**` — backend contract / image / review / session-auth tests.
- `docs/working/{current_task,backlog,tooling_notes}.md` — task state + P28-T05 row + ID-collision note.

## Summary
_To be filled on execution._ Planned: replace the inline-HTML dashboard (`/`, `/packet/{id}`)
with a session-authed JSON REST API (the contract in `deliverable_spec.md`) plus a React +
Ironvale SPA served at `/dashboard`. The API reuses the existing store calls
(`list_packets`/`list_baselines`/`get_baseline_for_url`/`set_baseline`/`set_review_status`) and
the existing Warden session login — no API-key, no `public_prefixes` entry. Images move from
inline base64 to `FileResponse` endpoints.

## Test Results
_To be filled on execution._ Target: new backend tests (API contract, image 200/404, review
mutations, session-auth enforced/rejected) + SPA vitest all passing; full backend suite green
except pre-existing Docker-only failures; ruff + mypy clean; SPA `tsc --noEmit` + vitest green.

## Efficiency

### Execute
- **Prompt Runs:** n/a
- **Conversation Restarts:** n/a
- **Notes:** None

### Review
- **Prompt Runs:** n/a
- **Conversation Restarts:** n/a
- **Notes:** None until reviewer fills this in.

### Close
- **Prompt Runs:** n/a
- **Conversation Restarts:** n/a
- **Notes:** None until closer fills this in.

## Review Notes
- Confirm `/api/*` and `/dashboard*` are NOT added to `WardenMiddleware` `public_paths`/
  `public_prefixes` and do NOT accept `X-Assay-Key` — they must require the session cookie.
- Confirm `POST /api/packets/{vid}/review` reuses the exact `set_baseline`/`set_review_status`
  store calls (and ideally `src/assay/api/service.py`) rather than introducing new semantics.
- ID-reuse risk: this packet reuses `TASK-0077` (already minted by P29; archive max is 0076 and
  `current_task.md` says next is 0078). The dir `P28-T05-TASK-0077` namespaces it; verify no
  overwrite of `tasks/P29-agent-surface-TASK-0077/` and that the collision is logged in
  `tooling_notes.md`.
- Verify the SPA mount serves deep links via index fallback and that `/` redirects to `/dashboard`.

## User Review
<!-- reviewer fills this section — executor must leave all fields below as-is -->
- **State:** pending
- **Summary:** [reviewer fills]
- **Resolution Mode:** [revise_current_task / replan_current_task / create_followup_task / close_task]

### Required Fixes
- None

### Open Questions To Log
- None

### Proposal Candidates To Log
- None

### Follow-Ups To Log
- None

### Residual Risks
- None

## Verification Review
<!-- verifier fills this section when applicable; otherwise leave defaults -->
- **State:** not_run
- **Summary:** No verifier configured

### Findings
- None

## Closure Decision
<!-- closer fills this section during final closeout -->
- **Decision:** pending
- **Reason:** [closer fills]

### Closure Blockers
- None

## Deliverable Checklist
- [ ] All seven contract endpoints implemented with the exact response shapes.
- [ ] `/api/*` + `/dashboard*` session-authed (no public-prefix, no X-Assay-Key).
- [ ] Image routes return PNG `FileResponse` / 404.
- [ ] Review endpoint reuses existing store logic; returns `review_status`.
- [ ] SPA built + served at `/dashboard` with index fallback; `/` redirects.
- [ ] Inline-HTML dashboard rendering retired/redirected.
- [ ] Working docs updated (current_task, backlog P28-T05 row, tooling_notes ID note).
- [ ] All tests passing (pytest + vitest).

## Blockers
None.
