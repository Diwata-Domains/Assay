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

- **Status:** pending

### P17-T03 — Packet detail view: full fields + inline screenshot

- **Status:** pending

---

## Phase 18 — Grain Integration Loop Closure

| ID | Task | Status | Dependencies | Notes |
|----|------|--------|--------------|-------|
| P18-T01 | Document canonical Grain<->Assay handshake for verify submit/status/ingest | pending | P12 complete | align payload and lifecycle expectations with Grain Phase 28 |
| P18-T02 | Add explicit `verification_id` tracking and idempotency behavior for resubmits | pending | P18-T01 | deterministic status and ingest retries |
| P18-T03 | Add optional transport mode for Grain `verify submit` compatibility | pending | P18-T01 | file-drop remains default; bridge transport is additive |
| P18-T04 | Add status endpoint/adapter contract for Grain `verify status` polling | pending | P18-T02, P18-T03 | return `pending`/`complete`/`failed` with stable schema |
| P18-T05 | Harden `assay submit` and `--submit` flows for packet provenance and duplicate handling | pending | P18-T02 | preserve no-loss local artifacts |
| P18-T06 | End-to-end integration tests with Grain-style verify flow fixtures | pending | P18-T03, P18-T04, P18-T05 | covers submit -> status -> ingest loop |
