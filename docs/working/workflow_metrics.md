# Workflow Metrics

---

## Phase 1 — Foundation — CLOSED 2026-04-15

### Task Summary
| Task | Status | Notes |
|------|--------|-------|
| P1-T01 Python scaffold | done | Clean first run |
| P1-T02 TypeScript SDK scaffold | done | Clean |
| P1-T03 Grain packet schema | done | CP-001 created and applied |
| P1-T04 Data contract schemas | done | 17 tests, all passing |
| P1-T05 Developer tooling | done | Makefile + pre-commit; all targets green |

### Phase Health
- **Blockers encountered:** 0
- **Open questions resolved:** Q1–Q10 (all)
- **Change proposals applied:** CP-001 (data_contracts.md §1 replaced with Grain Sentinel payload)
- **Tests at phase close:** 18 pytest / 1 vitest — all passing
- **Lint/typecheck at phase close:** clean

### System Improvements Identified

**Fix now (before Phase 2):**
- GB-001: `grain task prepare` does not detect stub packet files — project owner patching Grain
- GB-003: Execute prompt is fragile in live AI sessions — project owner patching Grain

**Batch next phase:**
- GB-002: No lightweight packet mode for small tasks — design decision for Grain v2

**Ignore:**
- None

---

## Phase 2 — CLI Skeleton — CLOSED 2026-04-15

### Task Summary
| Task | Status | Notes |
|------|--------|-------|
| P2-T01 CLI entrypoint (Typer) | done | All 5 command groups wired |
| P2-T02 assay.toml config loader | done | ConfigError → exit 2; tomllib stdlib |
| P2-T03 Stub policy enforcement | done | No-op — satisfied by P2-T01 |
| P2-T04 Global flags | done | `--verbose` added (was missing from P2-T01) |
| P2-T05 CLI unit tests | done | 37 pytest / 1 vitest passing |

### Phase Health
- **Blockers encountered:** 0
- **Open questions resolved:** none new
- **Change proposals:** none
- **Tests at phase close:** 37 pytest / 1 vitest — all passing
- **Lint/typecheck at phase close:** clean

### System Improvements Identified

**Fix now (before Phase 3):**
- GB-005: Phase review/close should be a hard gate in `grain workflow next` — not just a `stop_reason`. Currently bypassable by updating `current_focus.md` manually. Should require an explicit `grain phase close` command before routing to the next phase.

**Batch next phase:**
- None

**Ignore:**
- None

---

## Phase 3 — Playwright + Docker Runner — CLOSED 2026-04-16

### Task Summary
| Task | Status | Notes |
|------|--------|-------|
| P3-T01 Playwright Docker image | done | Dockerfile + run.js + package.json; `docker build` deferred |
| P3-T02 Python runner module | done | `runner.run()` wraps subprocess Docker call; fully mocked in tests |
| P3-T03 Artifact collection | done | `collect_artifacts()` + `ArtifactBundle`; 7 tests |
| P3-T04 Wire assay run command | done | CLI exits 0/3/1 per outcome; 6 mock tests |
| P3-T05 Runner integration test | done | `docker build` + `assay run --target https://example.com` → exit 0, result.json + screenshot.png written |

### Phase Health
- **Blockers encountered:** 1 (P3-T05: Docker PATH not set in Claude Code session — resolved by adding fallback path lookup in runner.py; package.json version pin fixed from `^1.44.0` to `1.44.0`)
- **Open questions resolved:** none new
- **Change proposals:** none
- **Tests at phase close:** 56 pytest / 1 vitest — all passing
- **Lint/typecheck at phase close:** clean

### System Improvements Identified

**Fix now (before Phase 4):**
- None

**Batch next phase:**
- None

**Ignore:**
- None

---

## Phase 4 — Task Packet Formatter — CLOSED 2026-04-16

### Task Summary
| Task | Status | Notes |
|------|--------|-------|
| P4-T01 Formatter module | done | `format_packet()` → Assay result payload dict; 13 tests |
| P4-T02 Packet file writer | done | `write_packet()` → `assay-<ts>-<uuid>.json`; 8 tests |
| P4-T03 Severity assignment | done | Satisfied by P4-T01 (`_SEVERITY_MAP`); no separate file |
| P4-T04 Integrate with runner | done | `assay run` now calls formatter + writer; packet path printed |
| P4-T05 Schema validation tests | done | 10 tests validating against `sentinel_payload.schema.json` |

### Phase Health
- **Blockers encountered:** 0
- **Open questions resolved:** none new
- **Change proposals:** CP-002 filed — rename "Sentinel" → "Assay" in `data_contracts.md §1` and schema files; `grain verify ingest` does not exist (Sentinel became Assay)
- **Tests at phase close:** 89 pytest / 1 vitest — all passing
- **Lint/typecheck at phase close:** clean

### System Improvements Identified

**Fix now (before Phase 5):**
- Apply CP-002: rename `sentinel_payload.schema.json` → `assay_payload.schema.json`, update `SENTINEL_PAYLOAD` → `ASSAY_PAYLOAD` in schemas/__init__.py and tests, update `data_contracts.md §1` heading and delivery model (pending owner approval)

**Batch next phase:**
- None

**Ignore:**
- None

---

## Phase 5 — FastAPI Ingest Layer + Auth — CLOSED 2026-04-20

### Task Summary
| Task | Status | Notes |
|------|--------|-------|
| P5-T01 assay key commands + key store | done | Pre-implemented; UUID v4 fix applied before handoff |
| P5-T02 FastAPI POST /ingest + Pydantic validation | done | 18 tests; clean first pass |
| P5-T03 X-Assay-Key auth middleware | done | app.state injection pattern; 401 on missing/invalid/revoked |
| P5-T04 format_sdk_packet + ingest→formatter→writer | done | TYPE_CHECKING guard for circular import; 7 new tests |
| P5-T05 assay serve → uvicorn | done | Lazy import; stub test updated to reflect real implementation |
| P5-T06 Auth integration tests | done | 9 tests; full round-trip, no auth mocking |

### Phase Health
- **Tasks completed:** 6
- **Blocked tasks:** 0
- **Prompt runs (phase total):** ~9
- **Avg prompt runs per completed task:** ~1.5
- **Manual interventions:** 0
- **First-pass success rate:** 5/6 (P5-T01 had UUID v4 drift corrected before handoff)
- **Rework count:** 1 (P5-T01 key id: `token_hex` → `uuid4`)
- **Drift incidents:** 1 (key id format vs data_contracts.md §3 — caught and fixed in same session)
- **Tests at phase close:** 141 pytest — all passing
- **Lint/typecheck at phase close:** clean
- **Phase duration:** 2026-04-18 → 2026-04-20

### System Improvements Identified

**Fix now (before Phase 6):**
- None

**Batch next phase:**
- `app.state` mutation in tests is a parallel-test fragility risk — switch to FastAPI `dependency_overrides` pattern when more endpoint tests accumulate
- `TYPE_CHECKING` import in `formatter.py` signals `assay.formatter` ↔ `assay.ingest` coupling — consider a shared `assay.models` module before Phase 6 adds more SDK-path code

**Ignore:**
- `assay serve` test mocks `uvicorn.run` — intentional, no real server binding needed at this stage
- Overlapping auth coverage between `test_ingest.py` and `test_auth.py` — serves distinct purposes

---

## Phase 6 — TypeScript Browser SDK — CLOSED 2026-04-20

### Task Summary
| Task | Status | Notes |
|------|--------|-------|
| P6-T01 AssaySDK constructor | done | Validates apiKey + endpoint; 8 vitest |
| P6-T02 captureScreenshot() via html2canvas | done | Strips data URI prefix; html2canvas mocked; 4 vitest |
| P6-T03 collectMetadata() | done | url, viewport, userAgent, capturedAt from DOM APIs; jsdom env; 5 vitest |
| P6-T04 capture() with POST to /ingest | done | Full payload assembly; fetch mocked; 10 vitest |
| P6-T05 ESM + CJS npm build | done | Dual tsconfig; exports field; clean tsc build |
| P6-T06 SDK → ingest integration test | done | 9 pytest; full payload → packet file; all fields verified |

### Phase Health
- **Tasks completed:** 6
- **Blocked tasks:** 0
- **Prompt runs (phase total):** ~6
- **Avg prompt runs per completed task:** 1.0
- **Manual interventions:** 0
- **First-pass success rate:** 6/6
- **Rework count:** 0
- **Drift incidents:** 0
- **Tests at phase close:** 150 pytest + 27 vitest — all passing
- **Lint/typecheck at phase close:** clean
- **Phase duration:** 2026-04-20

### System Improvements Identified

**Fix now (before Phase 7):**
- None

**Batch next phase:**
- `workflow next` routes to `task_execute` on a `done` task after `grain task close --quick` if `current_task.md` still points to it — workaround is manually clearing `current_task.md`. Expected: grain should check task status before routing.
- Phase start requires manual `grain task create` + status update to satisfy phase boundary gate — backlog entries alone insufficient. Consider `grain phase start` command.

**Ignore:**
- jsdom ExperimentalWarning from `@asamuzakjp/css-color` CJS/ESM interop — harmless noise from transitive html2canvas dep

---

---

## Phase 7 — Scheduler — CLOSED 2026-04-18

### Task Summary
| Task | Status | Notes |
|------|--------|-------|
| P7-T01 Schedule state persistence | done | `add/list/remove/update_last_run`; 15 tests |
| P7-T02 `assay schedule add/list/remove` CLI | done | `ScheduleConfig` added to config; 12 tests |
| P7-T03 Cron expression parser | done | `cron.py` via APScheduler `CronTrigger`; implemented with P7-T02; 5 validator tests |
| P7-T04 Scheduler loop | done | `run_scheduler()` + `_run_one()`; `assay schedule run`; 8 tests; CP-003 filed |
| P7-T05 Scheduler integration test | done | Full CLI lifecycle + job-fire + failure recording; 5 tests |

### Phase Health
- **Tasks completed:** 5
- **Blocked tasks:** 0
- **Prompt runs (phase total):** ~2 (continued from previous session)
- **Avg prompt runs per completed task:** ~0.4
- **Manual interventions:** 0
- **First-pass success rate:** 5/5
- **Rework count:** 1 (loop.py used `result.outcome` instead of `result.exit_code` — caught by mypy + test failure)
- **Drift incidents:** 0
- **Tests at phase close:** 187 pytest — all passing
- **Lint/typecheck at phase close:** ruff clean; mypy clean (8 pre-existing errors in keys/store.py)
- **Phase duration:** 2026-04-18

### System Improvements Identified

**Fix now (before Phase 8):**
- None

**Batch next phase:**
- `keys/store.py` has 8 pre-existing mypy errors (`list()` on `object` type) — same pattern fixed in schedule/store.py; carry forward to Phase 8 cleanup
- `assay schedule run` not in data_contracts.md §5 — CP-003 pending owner approval

**Ignore:**
- APScheduler missing py.typed marker — suppressed with `# type: ignore[import-untyped]`

---

---

## Phase 8 — Integration + E2E Testing — CLOSED 2026-04-20

### Task Summary
| Task | Status | Notes |
|------|--------|-------|
| P8-T01 E2E assay run path | done | subprocess-mocked Docker; full real pipeline; schema-valid packet; 5 tests |
| P8-T02 E2E SDK capture → ingest | done | Full real FastAPI + formatter + writer; schema-valid; 7 tests |
| P8-T03 Auth rejection E2E | done | Covered in P8-T02 (test_e2e_sdk.py); missing/invalid/revoked → 401 |
| P8-T04 Config precedence | done | explicit > local > global > defaults; error cases; 10 tests |
| P8-T05 Regression sweep | done | 209 pytest passing; ruff clean; 0 regressions |

### Phase Health
- **Tasks completed:** 5
- **Blocked tasks:** 0
- **Tests at phase close:** 209 pytest — all passing
- **Lint/typecheck at phase close:** ruff clean; mypy 8 pre-existing errors (keys/store.py) only
- **Phase duration:** 2026-04-20

### System Improvements Identified

**Fix now (before Phase 9):**
- None

**Batch next phase:**
- `keys/store.py` pre-existing mypy errors (list on object) — carry to Phase 9 cleanup
- CP-003 still pending: `assay schedule run` not in `data_contracts.md §5`

**Ignore:**
- Docker not available in CI/dev session — E2E run test uses subprocess mock (same pattern as P3-T04/P3-T05)

---

---

## Phase 9 — Packaging + Distribution — CLOSED 2026-04-21

### Task Summary
| Task | Status | Notes |
|------|--------|-------|
| P9-T01 Python package metadata | done | pyproject.toml: readme, license, authors, classifiers; README.md; `assay --version` verified |
| P9-T02 npm package metadata | done | package.json: author, license, keywords |
| P9-T03 Docker runner documentation | done | Build instructions added to README.md |
| P9-T04 First-run installation guide | done | README.md covers all paths |

### Phase Health
- **Tasks completed:** 4
- **Tests at phase close:** 209 pytest — all passing
- **Lint/typecheck at phase close:** clean

### Assay v0.1.0 Summary
- **Total phases:** 9
- **Total Python tests:** 209 passing
- **Total TypeScript tests:** 27 passing
- **CLI commands:** assay run, serve, schedule add/list/remove/run, key create/list/revoke, report
- **Pending CPs:** CP-002 (rename sentinel→assay in data_contracts.md), CP-003 (add schedule run to CLI spec)

---

### Phase 14 — HTML Report — CLOSED 2026-04-28

#### Task Summary
| Task | Status | Notes |
|------|--------|-------|
| P14-T01 assay report --format html | done | TASK-0032; inline base64 screenshots; 11 tests |
| P14-T02 --open flag | done | TASK-0033; webbrowser.open; 5 tests |

#### Phase Health
- **Tasks completed:** 2
- **Tests at phase close:** 266 pytest — all passing
- **Lint/typecheck at phase close:** clean

---

### Phase 15 — Watch Mode — CLOSED 2026-04-29

#### Task Summary
| Task | Status | Notes |
|------|--------|-------|
| P15-T01 assay run --watch | done | TASK-0034; polling, 500ms debounce, Ctrl+C exit; 9 tests |
| P15-T02 --watch-path glob support | done | TASK-0035; parse_watch_target, pathlib.glob filter; 9 new tests |

#### Phase Health
- **Tasks completed:** 2
- **Tests at phase close:** 284 pytest — all passing
- **Lint/typecheck at phase close:** clean

---

### Phase 16

#### Tasks

| Task | Status | Notes |
|------|--------|-------|
| P16-T01 SQLite schema and store module | done | TASK-0036; init_db, insert_packet, list_packets, import_packets; WAL mode; 13 tests |
| P16-T02 write packets on run and /ingest | done | TASK-0037; best-effort writes; 4 integration tests |
| P16-T03 assay report reads from SQLite | done | TASK-0038; list_packets replaces JSON glob; 6 new tests, updated existing |
| P16-T04 assay report --export json | done | TASK-0039; orthogonal to --format; 4 tests |
| P16-T05 assay store import --dir | done | TASK-0040; bulk upsert, skip malformed; 5 tests |

#### Phase Health
- **Tasks completed:** 5
- **Tests at phase close:** 315 pytest — all passing
- **Lint/typecheck at phase close:** clean

---
