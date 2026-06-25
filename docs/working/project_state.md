# Assay — Project State

> **This is a durable description of what Assay is, not a live phase tracker.**
> For the authoritative active phase and closed-phase ledger, see
> `docs/working/current_focus.md`. For task state, see `docs/working/backlog.md`.
> An earlier version of this file (produced 2026-06-02) claimed an active phase in the low
> twenties — that snapshot is stale and was superseded. This file does not declare an active
> phase; `docs/working/current_focus.md` is the single source of truth for that.

---

## What Assay Is

Assay is an independent visual verification layer for software projects. It provides:
1. **Automated screenshot capture** — Playwright + Docker runner, triggered by CLI or schedule
2. **Visual regression testing** — baseline capture, pixel diff engine, approve/reject workflow
3. **Hosted dashboard** — self-hosted web UI with single-admin auth, packet history, diff viewer
4. **Grain integration** — structured verification packets intended to satisfy the `grain verify`
   bridge contract (note: `grain verify ingest` does not yet exist in the Grain CLI — see CP-002)
5. **Browser SDK** — TypeScript/JS SDK for in-browser screenshot capture and ingest via `SDK.report()`
6. **Check library + Script DSL** — HTTP/header/auth checks and a JSON multi-step script format
7. **CI integration** — GitHub Action with non-zero exit on regression and commit status posting
8. **Multi-viewport testing** — capture and diff the same target across viewport widths

Assay is **independent of Grain** — it works standalone. The Grain integration is additive.
Assay does not depend on Grain's workflow system to function.

---

## Versions

| Version | Theme | Status |
|---|---|---|
| v0.1.0 | Foundation + CLI (runner, packet formatter, ingest + auth, SDK, scheduler, packaging) | RELEASED |
| v0.2.0 | Distribution + Grain integration (CI/CD, persistence, `assay report`, task tagging, daemon) | RELEASED |
| v0.3.0 | Visual Verification (HTML reports, watch mode, SQLite store, dashboard, pixel diff, baselines, CI/GitHub Action, check library, Script DSL, multi-viewport) | IMPLEMENTED (Phases 17–27), pending release in Phase 28 |
| v0.4.0 | Multi-viewport polish, alerts/webhooks, error visibility, client access layer | PLANNED (Phases 28–31 in backlog) |

The single authoritative phase ledger lives in `docs/working/current_focus.md`. Phases 1–27
are closed and archived; Phases 23 and 24 were never opened (no archive dirs exist).

---

## Active Constraints

- `assay schedule start` uses `os.fork()` — POSIX only. No Windows support until the daemon is refactored.
- Canonical docs require human approval before direct edits (standard Grain constraint).
- The Grain bridge (`grain verify ingest`) is not yet shipped in the Grain CLI (CP-002); the
  Assay→Grain verdict loop is not closed.
- Multi-user / org accounts are a prerequisite for any paid/hosted tier billing hooks.

---

## Open Directions

From `docs/working/open_questions.md` and the roadmap — open or deferred:

- **Monetization model:** deferred. API key infrastructure is sufficient for now.
- **API key storage encryption:** v1 uses bcrypt + plaintext JSON file; keychain support deferred.
- **Multi-browser support:** currently Chromium-only via Playwright; cross-browser is a future candidate.
- **Public sharing:** share a verification report via a public link (requires the client access layer first).
- **Assay SDK for Python:** server-side verification capture (not just browser SDK).
- **Adversarial AI code review:** a new verification MODE callable through the grain verify bridge
  (seeded as a backlog phase); greenfield, blocked on the bridge gap above.
