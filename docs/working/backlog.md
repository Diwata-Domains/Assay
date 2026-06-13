# Backlog

**Project:** Assay
**Last updated:** 2026-04-21

Status values: `pending` | `ready` | `in_progress` | `blocked` | `done`

---

## Phase 1 — Foundation ✓ CLOSED (5 tasks — archived to tasks/archive/phase-1/)

## Phase 2 — CLI Skeleton ✓ CLOSED (5 tasks — archived to tasks/archive/phase-2/)

## Phase 3 — Playwright + Docker Runner ✓ CLOSED (5 tasks — archived to tasks/archive/phase-3/)

## Phase 4 — Task Packet Formatter ✓ CLOSED (5 tasks — archived to tasks/archive/phase-4/)

## Phase 5 — FastAPI Ingest Layer + Auth ✓ CLOSED (6 tasks — archived to tasks/archive/phase-5/)

---

## Phase 6 — TypeScript Browser SDK ✓ CLOSED (6 tasks — archived to tasks/archive/phase-6/)

---

## Phase 7 — Scheduler ✓ CLOSED (5 tasks)

| ID | Task | Status | Dependencies | Notes |
|----|------|--------|--------------|-------|
| P7-T01 | Implement schedule state persistence (`~/.assay/schedules.json`) | done | P1-T04 | 15 tests |
| P7-T02 | Implement `assay schedule add/list/remove` fully | done | P7-T01, P2-T03 | 12 tests; ScheduleConfig added to config |
| P7-T03 | Integrate cron expression parser (APScheduler) | done | P7-T01 | implemented in P7-T02; cron.py |
| P7-T04 | Implement scheduler loop (invoke runner at scheduled times) | done | P7-T02, P7-T03, P3-T04 | 8 tests; CP-003 filed |
| P7-T05 | Scheduler integration test | done | P7-T04 | 5 tests |

---

## Phase 8 — Integration + E2E Testing ✓ CLOSED (5 tasks)

| ID | Task | Status | Dependencies | Notes |
|----|------|--------|--------------|-------|
| P8-T01 | E2E: `assay run` → subprocess mock → schema-valid packet | done | P4-T05, P3-T05 | 5 tests |
| P8-T02 | E2E: SDK capture → ingest → schema-valid packet | done | P6-T06 | 7 tests |
| P8-T03 | Auth rejection E2E | done | P5-T06 | covered in P8-T02 (test_e2e_sdk.py) |
| P8-T04 | Config precedence tests | done | P2-T05 | 10 tests |
| P8-T05 | Cross-phase regression sweep | done | all phases | 209 pytest passing |

---

## Phase 9 — Packaging + Distribution ✓ CLOSED (4 tasks)

| ID | Task | Status | Dependencies | Notes |
|----|------|--------|--------------|-------|
| P9-T01 | Finalize Python package metadata | done | P8 complete | pyproject.toml: readme, license, authors, classifiers; README.md |
| P9-T02 | Finalize npm package metadata | done | P8 complete | package.json: author, license, keywords |
| P9-T03 | Document Docker runner image | done | P8 complete | Build instructions in README.md |
| P9-T04 | First-run installation guide | done | P9-T01–P9-T03 | README.md: requirements, quick start, SDK, dev setup |

---

## v0.2.0

---

## Phase 10 — Distribution + CI ✓ CLOSED (2 tasks)

| ID | Task | Status | Dependencies | Notes |
|----|------|--------|--------------|-------|
| P10-T01 | PyPI publish workflow (GitHub Actions release job) | done | P9 complete | `.github/workflows/release.yml`; pypa/gh-action-pypi-publish |
| P10-T02 | GitHub Actions CI: pytest + ruff + mypy + vitest | done | P9 complete | `.github/workflows/ci.yml`; matrix Python 3.11/3.12 |

---

## Phase 11 — Screenshot Persistence + `assay report` ✓ CLOSED (3 tasks)

| ID | Task | Status | Dependencies | Notes |
|----|------|--------|--------------|-------|
| P11-T01 | Save SDK screenshot to disk on ingest; populate artifact_refs | done | P5 complete | `{verification_id}.png` in output dir; 4 tests |
| P11-T02 | Verify runner screenshot is copied + referenced in artifact_refs | done | P3-T05 | Copies to `{verification_id}.png` in output dir; 2 tests |
| P11-T03 | Implement `assay report` command (table + json + filter) | done | P4 complete | --format json, --filter key=val; 10 tests |

---

## Phase 12 — Grain Task Tagging + `assay submit` ✓ CLOSED (5 tasks)

| ID | Task | Status | Dependencies | Notes |
|----|------|--------|--------------|-------|
| P12-T01 | `assay run --task-id` flag; populate task_id in packet | done | P4 complete | 3 tests |
| P12-T02 | Grain auto-detection: read current_task.md / GRAIN_TASK_ID env | done | P12-T01 | detect_task_id(); 5 tests |
| P12-T03 | `assay submit --packet <path>` command + [grain] config section | done | P12-T01 | schema-validates before copy; 3 tests |
| P12-T04 | `assay run --submit` one-step flag | done | P12-T03 | 1 test |
| P12-T05 | SDK taskId passthrough to ingest payload | done | P6 complete | Optional task_id field in IngestPayload; 2 tests |

---

## Phase 13 — Background Scheduler (Daemon Mode) ✓ CLOSED (4 tasks)

| ID | Task | Status | Dependencies | Notes |
|----|------|--------|--------------|-------|
| P13-T01 | `assay schedule start`: background process + PID file | done | P7 complete | os.fork(); double-start prevention |
| P13-T02 | `assay schedule stop`: SIGTERM + PID cleanup | done | P13-T01 | stale PID detection |
| P13-T03 | `assay schedule status`: running/stopped + log file | done | P13-T01 | 11 tests total |
| P13-T04 | PID file locking; log file at ~/.assay/scheduler.log | done | P13-T01 | log redirect on daemon start |

---

## v0.2.0

---

## 14. Phase 14 — HTML Report

### P14-T01 — assay report --format html: single-file HTML with inline screenshots

- **Status:** done
- **Task ID:** TASK-0032

### P14-T02 — assay report --format html --open: auto-open in default browser

- **Status:** done
- **Task ID:** TASK-0033

---

## 15. Phase 15 — Watch Mode

### P15-T01 — assay run --watch: re-run on file/path change

- **Status:** done
- **Task ID:** TASK-0034

### P15-T02 — --watch-path glob option for file-based trigger

- **Status:** done
- **Task ID:** TASK-0035

---

## 16. Phase 16 — SQLite Output Store

### P16-T01 — SQLite schema and assay store module

- **Status:** done
- **Task ID:** TASK-0036

### P16-T02 — Write packets to SQLite on assay run and /ingest

- **Status:** done
- **Task ID:** TASK-0037

### P16-T03 — assay report reads from SQLite with filter and format preserved

- **Status:** done
- **Task ID:** TASK-0038

### P16-T04 — assay report --export json: backwards-compatible dump

- **Status:** done
- **Task ID:** TASK-0039

### P16-T05 — assay store import --dir: import existing assay JSON files

- **Status:** done
- **Task ID:** TASK-0040

---

## v0.3.0

---

## 17. Phase 17 — Web UI / Dashboard

### P17-T01 — Dashboard route at `/` served by assay serve

- **Status:** done
- **Task ID:** TASK-0041

### P17-T02 — Packet list view: table with outcome, severity, screenshot, timestamp

- **Status:** done
- **Task ID:** TASK-0042

### P17-T03 — Packet detail view: full fields + inline screenshot

- **Status:** done
- **Task ID:** TASK-0043

---

## 18. Phase 18 — Grain Integration Loop Closure

### P18-T01 — Document canonical Grain-Assay handshake

- **Status:** done
- **Task ID:** TASK-0044

### P18-T02 — verification_id idempotency for resubmits

- **Status:** done
- **Task ID:** TASK-0045

### P18-T03 — GET /status/{verification_id} endpoint

- **Status:** done
- **Task ID:** TASK-0046

### P18-T04 — Harden assay submit and --submit flows

- **Status:** done
- **Task ID:** TASK-0047

### P18-T05 — End-to-end integration tests for verify flow

- **Status:** done
- **Task ID:** TASK-0048

---

## 19. Phase 19 — Screenshot Quality + Docker Runner Validation

### P19-T01 — Replace html2canvas with html-to-image in the browser SDK

- **Status:** done
- **Task ID:** TASK-0049

### P19-T02 — Smoke-test the Docker runner build and run end-to-end

- **Status:** done
- **Task ID:** TASK-0050

### P19-T03 — SDK taskId and verificationId passthrough

- **Status:** done
- **Task ID:** TASK-0051

---

## 20. Phase 20 — Hosted Dashboard

### P20-T01 — Admin credentials config (env vars + assay admin set-password)

- **Status:** done
- **Task ID:** TASK-0052

### P20-T02 — Login page + JWT cookie session (GET /login, POST /login, GET /logout)

- **Status:** done
- **Task ID:** TASK-0053

### P20-T03 — Auth middleware protecting dashboard routes

- **Status:** done
- **Task ID:** TASK-0054

### P20-T04 — Key management UI (list, create, revoke from browser)

- **Status:** done
- **Task ID:** TASK-0055

### P20-T05 — Deployment config (Dockerfile, docker-compose, nginx, .env.example)

- **Status:** done
- **Task ID:** TASK-0056

---

## 21. Phase 21 — Visual Regression Testing

### P21-T01 — Baseline capture: mark a packet as the approved baseline for a URL

- **Status:** done
- **Task ID:** TASK-0057

### P21-T02 — Pixel diff engine: compare new capture against baseline, generate diff image

- **Status:** done
- **Task ID:** TASK-0058

### P21-T03 — Diff view in dashboard: before/after slider + highlighted regions

- **Status:** done
- **Task ID:** TASK-0059

### P21-T04 — Approve/reject workflow: accept new baseline or flag as regression

- **Status:** done
- **Task ID:** TASK-0060

### P21-T05 — assay run --compare: diff against baseline from CLI, exit 1 on regression

- **Status:** done
- **Task ID:** TASK-0061

---

## 22. Phase 22 — Developer Experience + SDK Integration

**Goal:** Remove the friction from first-time setup, API key creation, and SDK integration in app projects. The current flow requires knowing about assay.toml, generating bcrypt hashes manually, and wiring up the SDK without obvious guidance. This phase makes the full setup a guided 2-minute flow.

### P22-T01 — `assay init`: interactive first-run setup wizard

- **Status:** done
- Prompts for output dir, admin email, admin password (hashes inline), ingest port
- Writes `assay.toml` and prints `.env` block ready to paste
- Idempotent — safe to re-run; won't overwrite existing config without confirmation

### P22-T02 — `assay key create` UX: print curl example + SDK snippet with new key

- **Status:** done
- After printing the raw key, print a ready-to-use curl example and SDK constructor snippet
- Makes the key immediately usable without hunting docs

### P22-T03 — SDK: `AssaySDK.fromEnv()` factory + cleaner integration for app projects

- **Status:** done
- Add static `fromEnv()` that reads `ASSAY_ENDPOINT` and `ASSAY_API_KEY` env vars
- Add `useAssayCapture()` React hook in a new `@diwata-labs/assay-sdk/react` export
- Keep the existing constructor — `fromEnv()` is additive

### P22-T04 — SDK setup guide: framework-specific integration examples

- **Status:** done
- Vite/React quickstart: env vars, hook usage, capture on button press
- Next.js quickstart: server-side key, client-side capture component
- Lives in `packages/assay-sdk/docs/`

---

## 23. Phase 23 — Multi-step Playwright Test Scripts

### P23-T01 — Test script format: define steps (navigate, click, fill, screenshot) in a JS/TS file

- **Status:** done
- **Task ID:** TASK-0062

### P23-T02 — assay run --script <file>: execute script in Docker runner

- **Status:** done
- **Task ID:** TASK-0063

### P23-T03 — Script result packet: capture step-by-step screenshots + pass/fail per step

- **Status:** done
- **Task ID:** TASK-0064

### P23-T04 — Script library: built-in helpers (login flow, form fill, wait for selector)

- **Status:** done
- **Task ID:** TASK-0065

---

## 24. Phase 24 — CI/CD Integration

### P24-T01 — GitHub Actions action (diwata/assay-action@v1): run assay on PR

- **Status:** done

### P24-T02 — PR comment: post screenshot + diff summary as a PR comment

- **Status:** done

### P24-T03 — Status check: fail PR check if regression detected, pass if clean

- **Status:** done

### P24-T04 — assay ci config: assay.toml [ci] section for check behaviour and thresholds

- **Status:** done

---

## 25. Phase 25 — Functional + Integration Checks

**Goal:** Elevate Assay from a screenshot tool into a genuine verifier. Operators define named checks in `assay.toml` — HTTP assertions, header/CORS checks, auth enforcement, Playwright functional assertions, and JS console error detection. Failures produce structured results alongside visual packets.

### P25-T01 — `assay check` command + `[checks]` config block in assay.toml

- **Status:** done
- **Task ID:** TASK-0066

### P25-T02 — HTTP assertion engine

- **Status:** done
- **Task ID:** TASK-0067

### P25-T03 — Header + security config checks

- **Status:** done
- **Task ID:** TASK-0068

### P25-T04 — Playwright functional assertions in scripts

- **Status:** done
- **Task ID:** TASK-0069
- Console error detection: script fails if `console.error()` fires during page load or step execution
- Step-level pass/fail in result packet

### P25-T05 — Check results in dashboard + report output

- **Status:** done
- **Task ID:** TASK-0070
- `/checks` route in dashboard with table of check results; "Checks" link in nav
- `assay report --checks` prints check table; `--format json --checks` wraps in `{"packets": [...], "checks": [...]}`

---

## 26. Phase 26 — Auto Grain Task on Failure

**Goal:** Close the Grain ↔ Assay loop automatically. When a run detects a regression or a check fails, Assay creates a Grain task in the configured repo — no manual `assay submit` step required.

### P26-T01 — `[grain]` config section in assay.toml

- **Status:** pending
- Fields: `repo` (path to Grain repo root), `auto_create` (bool), `phase` (optional phase hint), `branch` (optional branch to write task on)
- Extends the existing `[grain]` section from Phase 18

### P26-T02 — Auto-create Grain task on visual regression

- **Status:** pending
- When `assay run --compare` detects a regression: create a Grain task with diff image attached, URL, baseline vs current screenshot, timestamp
- Task title: `Visual regression: <url> — <check_id or run_id>`

### P26-T03 — Auto-create Grain task on check failure

- **Status:** pending
- When `assay check` produces any failing result: create a Grain task per failing check
- Task includes: check id, type, target URL, assertion that failed, actual vs expected value
- Covers HTTP 500s, missing CORS headers, auth not enforced, console errors, functional assertion failures

### P26-T04 — Task deduplication

- **Status:** pending
- Before creating a task, check if an open Grain task already exists for the same check id + target
- Skip creation if duplicate; log deduplication decision in check result

### P26-T05 — Suggested remediation in task content

- **Status:** pending
- Each auto-created task includes a `remediation` field with a plain-language suggestion
- Example: CORS failure → "Add `Access-Control-Allow-Origin: https://apex.diwata.domains` to the response headers"
- Follows the same remediation pattern as `grain workflow guard`

---

## v0.4.0

---

## 27. Phase 27 — Multi-viewport Testing

### P27-T01 — assay run --viewports mobile,tablet,desktop: run same test at multiple widths

- **Status:** pending

### P27-T02 — Viewport results in dashboard: side-by-side view per capture session

- **Status:** pending

### P27-T03 — Viewport regression: diff per viewport independently, separate approve/reject

- **Status:** pending

---

## 28. Phase 28 — Alerts + Webhooks

### P28-T01 — Webhook config: assay.toml [alerts] with URL + events (fail, regression, pass)

- **Status:** pending

### P28-T02 — Webhook delivery: POST JSON payload on triggered events

- **Status:** pending

### P28-T03 — Slack integration: pre-built Slack webhook format with screenshot link

- **Status:** pending

### P28-T04 — Email alerts: SMTP config + HTML email on failure or regression

- **Status:** pending

---

## 29. Phase 29 — Multi-user + Org Accounts

### P29-T01 — User registration + login: email/password accounts, JWT sessions

- **Status:** pending

### P29-T02 — Org model: users belong to an org, data isolated per org

- **Status:** pending

### P29-T03 — Invite flow: invite teammates by email, accept via link

- **Status:** pending

### P29-T04 — Per-key access scoping: restrict API keys to specific projects or users

- **Status:** pending

### P29-T05 — Billing hooks: usage tracking per org (prep for paid tiers)

- **Status:** pending
