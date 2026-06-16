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
4 tasks done — archived to `tasks/archive/phase-9/`
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
5 tasks done — archived to `tasks/archive/phase-19/`
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

## Phase 23 — Grain Integration ✓ CLOSED
4 tasks done — archived to `tasks/archive/phase-23/`
Key deliverables: `grain verify` bridge, Grain auto-task creation from Assay results.

## Phase 24 — Error Recovery ✓ CLOSED
Archived to `tasks/archive/phase-24/`
Key deliverables: runner error handling, retry logic, structured error output in packets.

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

All v0.3.0 features are implemented across Phases 17–26. The release tag has not been cut yet.

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

### Phase 29 — Alerts and Webhooks

> **Status:** planned.

### P29-T01 — Webhook config: `assay.toml [alerts]`
- **Status:** pending
- **Description:** `[alerts]` block in `assay.toml` with `url` and `events` list (`fail`, `regression`, `pass`). Validated at startup.
- **Files:** `src/assay/config.py`

### P29-T02 — Webhook delivery
- **Status:** pending
- **Description:** POST JSON payload on triggered events. Retry on failure (3 attempts, exponential backoff). Non-blocking — never delays the run result.
- **Files:** `src/assay/alerts/webhook.py` (new)
- **Dependencies:** P29-T01

### P29-T03 — Slack integration
- **Status:** pending
- **Description:** Pre-built Slack webhook format with screenshot link and outcome summary.
- **Files:** `src/assay/alerts/slack.py` (new)
- **Dependencies:** P29-T02

### P29-T04 — Email alerts
- **Status:** pending
- **Description:** SMTP config in `assay.toml [alerts]`. HTML email on failure or regression.
- **Files:** `src/assay/alerts/email.py` (new)
- **Dependencies:** P29-T01

---

## Backlog Maintenance Rules

1. Backlog items must remain concrete and implementable
2. Closed phases are collapsed to a stub entry — verbose task descriptions live in the task archive
3. Version headers mark when features shipped or are targeted to ship
