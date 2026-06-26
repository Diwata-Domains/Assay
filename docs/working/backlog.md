# Backlog

**Project:** Assay

Status values: `pending` | `ready` | `in_progress` | `blocked` | `done`

---

## v0.1.0 — Foundation and Core Pipeline ✓ RELEASED

## Phase 1 — Foundation ✓ CLOSED
5 tasks done — archived to `tasks/archive/phase-1/`

## Phase 2 — CLI Skeleton ✓ CLOSED
5 tasks done — archived to `tasks/archive/phase-2/`

## Phase 3 — Playwright + Docker Runner ✓ CLOSED
5 tasks done — archived to `tasks/archive/phase-3/`

## Phase 4 — Task Packet Formatter ✓ CLOSED
5 tasks done — archived to `tasks/archive/phase-4/`

## Phase 5 — FastAPI Ingest Layer + Auth ✓ CLOSED
6 tasks done — archived to `tasks/archive/phase-5/`

## Phase 6 — TypeScript Browser SDK ✓ CLOSED
6 tasks done — archived to `tasks/archive/phase-6/`

## Phase 7 — Scheduler ✓ CLOSED
5 tasks done — archived to `tasks/archive/phase-7/`
Key deliverables: `assay schedule add/list/remove`, cron integration (APScheduler), scheduler loop.

## Phase 8 — Integration + E2E Testing ✓ CLOSED
5 tasks done — archived to `tasks/archive/phase-8/`
Key deliverables: E2E coverage for `assay run`, SDK capture → ingest, auth rejection, config precedence.

## Phase 9 — Packaging + Distribution ✓ CLOSED
7 tasks done — archived to `tasks/archive/phase-9/`
Key deliverables: PyPI metadata finalized, npm metadata finalized, Docker runner documented, first-run guide.

---

## v0.2.0 — Developer Experience ✓ RELEASED

## Phase 10 — Distribution + CI ✓ CLOSED
2 tasks done — archived to `tasks/archive/phase-10/`
Key deliverables: PyPI publish workflow, GitHub Actions CI (pytest + ruff + mypy + vitest).

## Phase 11 — Screenshot Persistence + `assay report` ✓ CLOSED
3 tasks done — archived to `tasks/archive/phase-11/`
Key deliverables: SDK screenshots saved to disk on ingest, `assay report` (table + json + filter).

## Phase 12 — Grain Task Tagging + `assay submit` ✓ CLOSED
5 tasks done — archived to `tasks/archive/phase-12/`
Key deliverables: `assay run --task-id`, Grain auto-detection, `assay submit --packet`, SDK taskId passthrough.

## Phase 13 — Background Scheduler (Daemon Mode) ✓ CLOSED
4 tasks done — archived to `tasks/archive/phase-13/`
Key deliverables: `assay schedule start/stop/status`, PID file locking, log file at `~/.assay/scheduler.log`.

## Phase 14 — HTML Report ✓ CLOSED
2 tasks done — archived to `tasks/archive/phase-14/`
Key deliverables: `assay report --format html` (single-file with inline screenshots), `--open` flag.

## Phase 15 — Watch Mode ✓ CLOSED
2 tasks done — archived to `tasks/archive/phase-15/`
Key deliverables: `assay run --watch`, `--watch-path` glob option.

## Phase 16 — SQLite Output Store ✓ CLOSED
5 tasks done — archived to `tasks/archive/phase-16/`
Key deliverables: SQLite schema, packets written on run and ingest, `assay report` reads from SQLite, `assay store import`.

## Phase 17 — Web UI / Dashboard ✓ CLOSED
3 tasks done — archived to `tasks/archive/phase-17/`
Key deliverables: dashboard at `/`, packet list view, packet detail view with inline screenshot.

## Phase 18 — Diff Engine + Visual Regression ✓ CLOSED
5 tasks done — archived to `tasks/archive/phase-18/`
Key deliverables: pixel-level diff engine, before/after overlay slider in dashboard, regression detection.

## Phase 19 — Baseline Management ✓ CLOSED
3 tasks done — archived to `tasks/archive/phase-19/`
Key deliverables: per-check approve/reject on baseline updates, baseline stored as separate artifact.

## Phase 20 — CI Integration + GitHub Action ✓ CLOSED
5 tasks done — archived to `tasks/archive/phase-20/`
Key deliverables: `action.yml` GitHub Action, non-zero exit on regression, commit status posting.

## Phase 21 — Check Library ✓ CLOSED
5 tasks done — archived to `tasks/archive/phase-21/`
Key deliverables: HTTP checks (status code, response time, redirect chain), header checks (CSP, X-Frame-Options), auth checks.

## Phase 22 — `assay init` ✓ CLOSED
4 tasks done — archived to `tasks/archive/phase-22/`
Key deliverables: interactive first-run wizard, `AssaySDK.fromEnv()`, `useAssayCapture()` React hook.

## Phase 23 — Grain Integration ⃠ NEVER OPENED
Planned (`grain verify` bridge, Grain auto-task creation) but never opened — no archive
directory exists for this phase. The phase sequence skips 23. Bridge work is tracked in the
v0.4.0 audit phases below (and CP-002 records the `grain verify ingest` gap).

## Phase 24 — Error Recovery ⃠ NEVER OPENED
Planned (runner error handling, retry logic, structured error output) but never opened — no
archive directory exists for this phase. The phase sequence skips 24. Error-visibility work
is carried forward into v0.4.0 Phase 30 below.

## Phase 25 — Script DSL ✓ CLOSED
5 tasks done — archived to `tasks/archive/phase-25/`
Key deliverables: JSON script format (navigate, fill, click, wait, capture), script validation, `assay run --script`.

## Phase 26 — Self-check + Remediation ✓ CLOSED
5 tasks done — archived to `tasks/archive/phase-26/`
Key deliverables: `assay check` built-in verification suite, `suggest_remediation()`, remediation field in auto-created packets.

## Phase 27 — Multi-viewport Testing ✓ CLOSED
1 task done — archived to `tasks/archive/phase-27/`

---

## v0.3.0 — Visual Verification (implemented, pending release)

All v0.3.0 features are implemented across Phases 14–27 (Phases 23 and 24 were never opened).
The release tag has not been cut yet — see Phase 28 below.

---

## v0.4.0 — Multi-viewport and Alerts

### Phase 28 — Multi-viewport Testing

> **Status:** planned — first v0.4.0 feature phase.

### P28-T01 — `assay run --viewports mobile,tablet,desktop`
- **Status:** pending
- **Description:** Run the same test at multiple viewport widths in a single invocation. Each viewport produces its own packet and screenshot. Baseline and diff tracked per viewport independently.
- **Files:** `src/assay/runner/runner.py`, `src/assay/cli/main.py`, tests

### P28-T02 — Viewport results in dashboard
- **Status:** pending
- **Description:** Side-by-side view per capture session in the dashboard. Filter and diff by viewport.
- **Files:** dashboard routes, templates
- **Dependencies:** P28-T01

### P28-T03 — Viewport regression: diff per viewport independently
- **Status:** pending
- **Description:** Separate approve/reject per viewport. Regression in one viewport does not affect others.
- **Files:** `src/assay/diff/engine.py`, baseline service
- **Dependencies:** P28-T01

---

### Deferred — Alerts and Webhooks (formerly "Phase 29 — Alerts and Webhooks")

> **Status:** deferred / unnumbered. Relocated 2026-06-25 — the "Phase 29" number now belongs
> to the authoritative **## Phase 29 — Agent-Usable Verification Surface** below. These alert
> tasks keep `ALERT-T0x` IDs to avoid colliding with the real P29-T0x agent-surface tasks.

### ALERT-T01 — Webhook config: `assay.toml [alerts]`
- **Status:** pending
- **Description:** `[alerts]` block in `assay.toml` with `url` and `events` list (`fail`, `regression`, `pass`). Validated at startup.
- **Files:** `src/assay/config.py`

### ALERT-T02 — Webhook delivery
- **Status:** pending
- **Description:** POST JSON payload on triggered events. Retry on failure (3 attempts, exponential backoff). Non-blocking — never delays the run result.
- **Files:** `src/assay/alerts/webhook.py` (new)
- **Dependencies:** ALERT-T01

### ALERT-T03 — Slack integration
- **Status:** pending
- **Description:** Pre-built Slack webhook format with screenshot link and outcome summary.
- **Files:** `src/assay/alerts/slack.py` (new)
- **Dependencies:** ALERT-T02

### ALERT-T04 — Email alerts
- **Status:** pending
- **Description:** SMTP config in `assay.toml [alerts]`. HTML email on failure or regression.
- **Files:** `src/assay/alerts/email.py` (new)
- **Dependencies:** ALERT-T01

---

### Error Visibility + Screenshot Serving (deferred appendix; see authoritative ## Phase 30 below)

> **Status:** planned.

### P30-T01 — Dashboard error panel
- **Status:** pending
- **Description:** Filter packets by `outcome=fail`. Show error message and stack trace inline on the packet detail view. Add a dedicated `/errors` tab in the dashboard nav.
- **Files:** dashboard routes, templates

### P30-T02 — `assay logs` CLI command
- **Status:** pending
- **Description:** `assay logs` tails `~/.assay/scheduler.log` and the ingest server log. `--lines N` for history, `--follow` for live tail.
- **Files:** `src/assay/cli/logs.py` (new), `src/assay/cli/main.py`

### P30-T03 — `/screenshots/{id}` serving endpoint
- **Status:** pending
- **Description:** `assay serve` exposes a static route for screenshot artifacts by packet ID. Returns the image with correct content-type. Enables stable shareable URLs for use in CI comments and Slack messages.
- **Files:** `src/assay/server/routes.py`

### P30-T04 — `/errors` JSON endpoint
- **Status:** pending
- **Description:** `GET /errors` returns recent failed packets as structured JSON (id, project, outcome, error, timestamp). Useful for CI integrations and external dashboards. Protected by admin JWT.
- **Files:** `src/assay/server/routes.py`

---

### Phase 31 — Client Access Layer

> **Status:** planned.

### P31-T01 — `POST /admin/keys` programmatic key creation
- **Status:** pending
- **Description:** Admin API endpoint to create a new API key for a named project. Protected by admin JWT. Returns the key once — same semantics as `assay key create`. Eliminates the need to SSH in and run the CLI for each client.
- **Files:** `src/assay/server/routes.py`, `src/assay/auth/keys.py`

### P31-T02 — Project entity on API keys
- **Status:** pending
- **Description:** Add a `project` field to the API key record. Ingest endpoint associates each packet with the key's project. Existing keyless behaviour unchanged.
- **Files:** `src/assay/auth/keys.py`, `src/assay/schemas/`, SQLite migration
- **Dependencies:** P31-T01

### P31-T03 — Dashboard project filter
- **Status:** pending
- **Description:** Dashboard filters packets to the authenticated key's project. Admin JWT sees all projects. Project key sees only its own data.
- **Files:** dashboard routes, templates, `src/assay/server/routes.py`
- **Dependencies:** P31-T02

### P31-T04 — Read-only viewer login
- **Status:** pending
- **Description:** A client authenticates via their project API key on a `/login` page and receives a short-lived read-only JWT scoped to their project. They can browse their project dashboard without access to admin functions or other projects.
- **Files:** `src/assay/auth/viewer.py` (new), dashboard login template
- **Dependencies:** P31-T03

---

## Phase 28 — Release v0.3.0 + Documentation Reconciliation

> Audit (2026-06-25): v0.3.0 "Visual Verification" (dashboard, pixel diff, baselines, CI/GitHub Action, check library, Script DSL) is IMPLEMENTED across Phases 17-27 but never released — pyproject is still 0.2.0 and the public ROADMAP lists shipped features as "Coming." Four planning docs disagree on the active phase and CLAUDE.md's task-ID counter is off by ~45 (agents mint colliding IDs). Make the release and the docs trustworthy before building further.

### P28-T01 — Cut and publish assay-kit v0.3.0
- **Status:** draft
- **Description:** Reconcile pyproject version + ROADMAP + CHANGELOG to on-disk reality; tag and publish assay-kit 0.3.0 via an agent-triggerable release path (mirror Diwata's CI-driven release.yml). The code already exists — this is a release, not a build.
- **Dependencies:** P28-T02

### P28-T02 — Reconcile the four phase-state docs to one truth
- **Status:** draft
- **Description:** current_focus / backlog / current_task / project_state give four different active phases. Pick the on-disk truth (archive reaches Phase 27 / TASK-0076), collapse closed phases, fix the claimed-but-absent phase-23/24 archive entries, reduce to a single authoritative Current Phase + ledger.
- **Dependencies:** none

### P28-T03 — Fix CLAUDE.md task-ID counter
- **Status:** draft
- **Description:** CLAUDE.md and AGENTS.md carried a stale hardcoded task-ID counter (off by ~45) while the archive reaches TASK-0076 — agents following it mint colliding IDs. Fixed in the 2026-06-25 reconciliation: both now derive the next ID from the archive max rather than a hardcoded number.
- **Dependencies:** none

### P28-T04 — Refresh canonical product_scope.md
- **Status:** draft
- **Description:** Canonical product_scope.md still lists dashboard / multi-user / OAuth as v1 NON-goals though dashboard + auth are shipped. Human-approved change proposal to refresh it to the real surface.
- **Dependencies:** none

### P28-T05 — Assay dashboard SPA (Ironvale)
- **Status:** ready
- **Description:** Replace the inline-HTML dashboard in `src/assay/ingest/app.py` (the `/`, `/packet/{id}` f-string HTML pages) with a React + Ironvale single-page app in `apps/assay-dashboard` (mirrors the `apps/diwa-web` Vite/React 19/ironvale/react-router/tanstack-query stack) backed by a session-authed JSON REST API. The API reuses the existing store logic and the same Warden session login as the HTML dashboard (NOT API-key, NOT in `public_prefixes`): `GET /api/packets` (list, filter by outcome/task_id, paginated), `GET /api/packets/{vid}` (detail with `has_baseline`/`has_candidate`/`has_diff`), `GET /api/packets/{vid}/{candidate,baseline,diff}.png` (FileResponse / 404), `POST /api/packets/{vid}/review` ({action: approve|reject|set-baseline} → review_status). The built SPA mounts at `/dashboard` + `/dashboard/assets/*` behind `WardenMiddleware` with an SPA index fallback; `/` redirects to `/dashboard`. Splits presentation from data access and is the precondition for the seeded dashboard work (P28-T02 viewport side-by-side, P30-T01 error panel, P31-T03 project filter).
- **Files:** `apps/assay-dashboard/**` (new), `src/assay/ingest/api.py` (new) + `src/assay/ingest/app.py`, `tests/`, `tasks/P28-T05-TASK-0077/`
- **Task packet:** `tasks/P28-T05-TASK-0077/` (TASK-0077 — see the ID-reuse note in `current_task.md` / `tooling_notes.md`)
- **Dependencies:** none

## Phase 29 — Agent-Usable Verification Surface ✓ DONE

> Make Assay fully familiar-drivable (agent-usable, agent-agnostic). The CLI is the most complete surface, but the MCP server was a STUB returning canned data — it misled agents into believing they triggered a real run (the biggest agent-correctness risk). The browser SDK is NOT the agent path. Baseline approval was dashboard-only.
>
> **Closed 2026-06-25 (TASK-0077).** The MCP server is now engine-backed (`src/assay/api/mcp.py`
> dispatches to the shared `src/assay/api/service.py`) and API-key-authed; a machine-readable
> manifest lives at `src/assay/contracts/` and `GET /mcp/manifest`; `--format json` and
> non-interactive `assay init` shipped; baselines are manageable headlessly via CLI
> (`assay baseline …`) and API-key HTTP (`/baselines*`); README/AGENTS document the agent path
> and the `assay-sdk` name drift is fixed.

### P29-T01 — Replace the MCP stub with a real engine-backed server
- **Status:** done
- **Description:** Wired run_verification/get_report in src/assay/api/mcp.py to the real runner + store/diff via a shared `assay.api.service` engine layer (no canned JSON). `/mcp/*` now requires `X-Assay-Key`.
- **Dependencies:** none

### P29-T02 — Expand the MCP/HTTP tool contract to full-loop coverage
- **Status:** done
- **Description:** Tools now cover submit/run, status poll (`get_status`), structured `get_report`, `list_runs` (by task/outcome), and baseline `approve`/`reject`/`set`/`list`. One machine-readable tool+schema+endpoint manifest published in `src/assay/contracts` and served at `GET /mcp/manifest`.
- **Dependencies:** P29-T01

### P29-T03 — JSON output everywhere + non-interactive init
- **Status:** done
- **Description:** `--format json` added to run/check/schedule list/key create/key list (and baseline). `assay init --non-interactive`/`--yes` runs with no prompts/getpass (flags or `ASSAY_ADMIN_EMAIL`/`ASSAY_ADMIN_PASSWORD`) and `--format json` emits the env block. `assay run --format json` emits verification_id + outcome + packet_path.
- **Dependencies:** none

### P29-T04 — Headless baseline approve/reject/set
- **Status:** done
- **Description:** `assay baseline {list,set,approve,reject}` (with `--format json`) plus API-key HTTP (`GET /baselines`, `POST /baselines/{set,approve,reject}`) drive the diff/baseline workflow without the dashboard.
- **Dependencies:** P29-T01

### P29-T05 — Agent-access docs + SDK reconciliation
- **Status:** done
- **Description:** README + AGENTS now have an "Agent / programmatic access" section (CLI / POST /ingest with JSON Schema / MCP — NOT the browser SDK). Fixed the `@diwata-labs/assay-sdk` vs `assay-sdk` README name drift.
- **Dependencies:** none

## Phase 30 — Adversarial AI Code Review (v-next verification mode)

> Founder-decided v-next: adversarial / multi-agent AI code review as a NEW verification MODE, callable through the grain verify bridge, populating grain review's approved/needs_fix verdict (memory: assay-vnext-adversarial-review). Greenfield — no LLM/agent code in src/ today. BLOCKED-BY: the bridge is half-real — CP-002 records that `grain verify ingest` does not exist in the current Grain CLI; close that first or the verdict never flows back.

### P30-T01 — Close the grain verify bridge gap (cross-product, Grain side)
- **Status:** blocked
- **Description:** Confirm/implement `grain verify ingest` in the Grain CLI so the Assay→Grain verdict loop closes (resolve CP-002). Until then, assay submit only drops a file in an inbox; the agent-to-agent loop is not closed.
- **Dependencies:** Grain CLI (grain verify ingest)

### P30-T02 — Define the code_review verdict contract (change proposal)
- **Status:** done
- **Description:** Verdict contract landed in `src/assay/review/verdict.py` — deterministic verdict→outcome→grain-review mapping (pass→approved, fail→needs_fix, inconclusive→needs_human), `CodeReviewResult`/`CodeReviewFinding` domain types, and `format_review_packet`. CP-005 (the `review` block + `code_review` issue_type schema change) is filed in change_proposals.md and pending human approval; until it lands the packet stays schema-valid by reusing `issue_type=bug_finding` and folding findings into summary + artifact_refs.
- **Dependencies:** none

### P30-T03 — Multi-agent code_review runner
- **Status:** done
- **Description:** `src/assay/review/runner.py` — adversarial proposer(s)/critic + judge producing a deterministic verdict re-derived from the surviving findings (not the judge's free-text label); provider-neutral `LLMClient` Protocol with an opt-in Anthropic default behind the `review` extra; persists transcripts + findings as artifacts.
- **Dependencies:** P30-T02

### P30-T04 — Non-URL verification input (git diff / refs / file set)
- **Status:** done
- **Description:** `src/assay/review/diff.py` `gather_diff()` supports repo path + base/head refs and/or an explicit changed-file list, or a pre-gathered diff string. `run_review`/`run_code_review` accept diff input instead of a URL.
- **Dependencies:** P30-T03

### P30-T05 — Wire code_review as a bridge-callable, packet-emitting mode
- **Status:** done
- **Description:** `assay review --repo . --base <ref> --head <ref> --task-id TASK-XXXX --verification-id VERIFY-XXXX-NNN [--submit] [--format json]` drives the runner via `service.run_code_review`, formats a schema-valid packet (outcome from the verdict, `verification_id` passthrough, findings + transcripts as artifact_refs), writes it to the store, and reuses `_do_submit()` for the Grain handoff. Mirrors the run→submit packet path.
- **Dependencies:** P30-T04, P30-T01

### P30-T06 — Real MCP code_review tool + integration tests
- **Status:** done
- **Description:** `code_review` tool added to the MCP surface (`/mcp/call` + manifest + committed `tool_manifest.json`), X-Assay-Key auth like the other tools, inputs {repo, base, head, diff, task_id, verification_id} → injectable/fake LLM client → returns {verdict, outcome, verification_id, status}. Integration tests in `tests/test_review_bridge.py`: fixture git repo + fake LLM, schema-valid packet, verdict→outcome mapping, verification_id passthrough, `_do_submit` copy, and the MCP tool over `/mcp/call` — both approved and needs_fix.
- **Dependencies:** P30-T05

## Backlog Maintenance Rules

1. Backlog items must remain concrete and implementable
2. Closed phases are collapsed to a stub entry — verbose task descriptions live in the task archive
3. Version headers mark when features shipped or are targeted to ship
