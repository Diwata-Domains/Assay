# Current Focus

## Current Phase
Phase 15 — Watch Mode

<!-- grain-phase-closed: 14 -->

---

## Active Focus

Phase 14 complete (HTML report with inline screenshots + --open flag). Now on Phase 15: watch mode.
- Phase 15: `assay run --watch` (file watcher, debounce, re-run on change)
- Phase 16: SQLite output store (replace flat JSON, `assay store import`)

v0.3.0 planned:
- Phase 17: Web UI / Dashboard (served by `assay serve`, powered by SQLite)

---

## Immediate Priorities

1. P15-T01: `assay run --watch` — re-run on file/path change
2. P15-T02: `--watch-path <glob>` option
3. → Phase 16: SQLite store

---

## Active Constraints

- Canonical docs require human approval before direct edits
- `assay schedule start` uses `os.fork()` — POSIX only (no Windows support)
- Phase 17 (web UI) depends on Phase 16 (SQLite) being complete first
- Grain has no `grain verify ingest` command yet — submitted packets sit unread (logged in tooling_notes.md)
