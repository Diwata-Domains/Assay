# Current Focus

## Current Phase
Phase 28 — Release v0.3.0 + Documentation Reconciliation

> **Status:** v0.3.0 "Visual Verification" (dashboard, pixel diff, baselines, CI/GitHub
> Action, check library, Script DSL, multi-viewport) is IMPLEMENTED across Phases 17–27 but
> not yet released — `pyproject` is still 0.2.0 and the public ROADMAP lists shipped features
> as "Coming." Phase 28 cuts the release and makes the planning docs trustworthy.
> **Release being cut:** v0.3.0 (founder decision).
> **Next milestone:** v0.4.0 — Phases 28–30 are already seeded in `docs/working/backlog.md`
> (multi-viewport polish, alerts/webhooks, error visibility, client access layer).
> **Last released:** v0.2.0 (Phase 13 close).

> **Phase 29 — Agent-Usable Verification Surface: ✓ DONE (2026-06-25, TASK-0077).** The MCP
> server is engine-backed and API-key-authed, a machine-readable agent manifest is published
> (`src/assay/contracts/`, `GET /mcp/manifest`), `--format json` + non-interactive `assay init`
> shipped, baselines are managed headlessly via `assay baseline …` and `/baselines*`, and the
> agent path is documented in README/AGENTS. See `docs/working/backlog.md` → "Phase 29".

> **Phase 30 — Adversarial AI Code Review: ✓ IMPLEMENTED (2026-06-25).** The new code_review
> verification MODE is bridge-callable end-to-end: `src/assay/review/` holds the verdict
> contract + multi-agent (proposer/critic/judge) runner + non-URL diff input; `assay review
> --repo --base --head --task-id --verification-id [--submit] [--format json]` and the MCP
> `code_review` tool (`/mcp/call`, X-Assay-Key) both drive the runner via
> `service.run_code_review`, map the verdict to a packet outcome (approved→pass,
> needs_fix→fail), emit a schema-valid packet (verification_id passthrough), persist it, and
> reuse `_do_submit` for the Grain handoff. Covered by `tests/test_review_bridge.py` (fixture
> repo + fake LLM, both verdicts). **Still open:** P30-T01 — the Grain-side `grain verify
> ingest` command does not exist (CP-002), so the verdict file lands in the Grain inbox but the
> agent-to-agent loop is not yet closed; and CP-005 (the `review` block + `code_review`
> issue_type schema change) is pending human approval, so packets currently reuse
> `issue_type=bug_finding`. See `docs/working/backlog.md` → "Phase 30".

All execution phases through Phase 27 are CLOSED and archived under `tasks/archive/phase-{N}/`.
The Closed-Phase Ledger below is the authoritative one-line status of every closed phase;
full task detail lives in the archive. This file names the focus; `docs/working/backlog.md`
owns task state.

## Immediate Priorities
1. P28-T01: Cut and publish `assay-kit` v0.3.0 — reconcile `pyproject` version + ROADMAP +
   CHANGELOG to on-disk reality; tag and publish via an agent-triggerable release path.
2. P28-T02: Reconcile the four phase-state docs to one truth (this file is the source of
   truth; `current_task.md` / `project_state.md` defer to it).
3. P28-T03: Fix `CLAUDE.md`'s task-ID counter (archive reaches TASK-0076 → next is TASK-0077).
4. P28-T04: Refresh canonical `product_scope.md` via change proposal (dashboard + auth are
   shipped, not v1 non-goals).

## Active Constraints
- Canonical docs (`docs/canonical/`) require human approval before direct edits — file a
  change proposal in `docs/working/change_proposals.md` first.
- `assay schedule start` uses `os.fork()` — POSIX only (no Windows support).
- The Grain bridge (`grain verify ingest`) is half-real — CP-002 records that the command
  does not exist in the current Grain CLI. The Assay→Grain verdict loop is not yet closed.

## Do Not Work On Right Now
- v0.4.0 feature phases (29–31 in the backlog) — gated behind the v0.3.0 release + doc
  reconciliation in this phase.
- Direct edits to `docs/canonical/` — change proposal only.

## Milestone Direction (v0.3.0)
- Theme: Visual Verification (hosted dashboard, pixel-diff regression, baselines, CI/GitHub
  Action, HTTP/header/auth check library, JSON Script DSL, multi-viewport).
- Phases of record: 17–27.
- Next milestone: v0.4.0 — multi-viewport polish, alerts/webhooks, error visibility, and a
  client access layer (Phases 28–31 in the backlog).

---

## Closed-Phase Ledger
One line per closed phase. This is the single authoritative status list.
Anything described as "active" above must NOT appear here, and vice versa.
Task counts and IDs are derived from `tasks/archive/phase-{N}/`.

| Phase | Title | Tasks | Milestone |
|-------|-------|-------|-----------|
| 1  | Foundation | 5 | v0.1.0 |
| 2  | CLI Skeleton | 5 | v0.1.0 |
| 3  | Playwright + Docker Runner | 5 | v0.1.0 |
| 4  | Task Packet Formatter | 5 | v0.1.0 |
| 5  | FastAPI Ingest Layer + Auth | 6 | v0.1.0 |
| 6  | TypeScript Browser SDK | 6 | v0.1.0 |
| 7  | Scheduler | 5 | v0.1.0 |
| 8  | Integration + E2E Testing | 5 | v0.1.0 |
| 9  | Packaging + Distribution | 7 | v0.1.0 |
| 10 | Distribution + CI | 2 | v0.2.0 |
| 11 | Screenshot Persistence + `assay report` | 3 | v0.2.0 |
| 12 | Grain Task Tagging + `assay submit` | 5 | v0.2.0 |
| 13 | Background Scheduler (Daemon Mode) | 4 | v0.2.0 |
| 14 | HTML Report | 2 | v0.3.0 |
| 15 | Watch Mode | 2 | v0.3.0 |
| 16 | SQLite Output Store | 5 | v0.3.0 |
| 17 | Web UI / Dashboard | 3 | v0.3.0 |
| 18 | Diff Engine + Visual Regression | 5 | v0.3.0 |
| 19 | Baseline Management | 3 | v0.3.0 |
| 20 | CI Integration + GitHub Action | 5 | v0.3.0 |
| 21 | Check Library | 5 | v0.3.0 |
| 22 | `assay init` + SDK ergonomics | 4 | v0.3.0 |
| 25 | Script DSL | 5 | v0.3.0 |
| 26 | Self-check + Remediation | 5 | v0.3.0 |
| 27 | Multi-viewport Testing | 1 | v0.3.0 |

Notes:
- Phases 23 and 24 were planned (Grain Integration, Error Recovery) but were never opened —
  no archive directories exist for them under `tasks/archive/`. The phase sequence skips them.
- Task IDs restart once: Phases 1–5 use TASK-0001…0026; Phase 6 restarts at TASK-0001 and
  runs monotonically to TASK-0076 at Phase 27. The current global max is **TASK-0076**, so
  the next packet is **TASK-0077** (see `CLAUDE.md`).

v0.1.0 and v0.2.0 are RELEASED. v0.3.0 is IMPLEMENTED (Phases 17–27) and pending release in
Phase 28.

## Upcoming Phase Sequence
1. v0.4.0 — multi-viewport polish, alerts/webhooks, error visibility, client access layer
   (Phases 28–31 in `docs/working/backlog.md`); further agent-usability and adversarial AI
   code-review work seeded as Phases 29–30 of the audit backlog.
