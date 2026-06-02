# Assay — Project State

**Produced:** 2026-06-02
**Phase:** 21 closed; Phase 22 next (not started)
**Source:** Diwata-Infra Phase 18 audit (P18-T01)

---

## What Assay Is

Assay is an independent visual verification layer for software projects. It provides:
1. **Automated screenshot capture** — Playwright + Docker runner, triggered by CLI or schedule
2. **Visual regression testing** — baseline capture, pixel diff engine, approve/reject workflow
3. **Hosted dashboard** — self-hosted web UI with single-admin auth, packet history, diff viewer
4. **Grain integration** — structured verification packets that satisfy the `grain verify` bridge contract; `grain verify ingest` ingests Assay results directly
5. **Browser SDK** — TypeScript/JS SDK for in-browser screenshot capture and ingest via SDK.report()

Assay is **independent of Grain** — it works standalone. The Grain integration is additive. Assay does not depend on Grain's workflow system to function.

---

## Versions Shipped

| Version | Theme | Key Deliverables |
|---|---|---|
| v0.1.0 | Foundation + CLI | Playwright+Docker runner, task packet formatter, FastAPI ingest layer + auth, TypeScript browser SDK, APScheduler, integration tests, packaging |
| v0.2.0 | Distribution + Grain integration | CI/CD (PyPI + GitHub Actions), screenshot persistence, `assay report`, Grain task tagging + `assay submit`, background scheduler daemon |
| v0.3.0 | Hosted product | HTML reports, watch mode, SQLite output store, web UI/dashboard, Grain integration loop closure, screenshot quality improvements (html-to-image), hosted dashboard (auth, key management UI, Dockerfile), visual regression testing |

---

## Phase History

| Phase | Theme | Status |
|---|---|---|
| 1–9 | Foundation: CLI, Playwright, SDK, scheduler, packaging | CLOSED |
| 10–13 | v0.2.0: CI/CD, screenshot persistence, Grain tagging, daemon | CLOSED |
| 14 | HTML report | CLOSED |
| 15 | Watch mode | CLOSED |
| 16 | SQLite output store | CLOSED |
| 17 | Web UI / Dashboard | CLOSED |
| 18 | Grain integration loop closure | CLOSED |
| 19 | Screenshot quality + Docker validation | CLOSED |
| 20 | Hosted dashboard (auth + key UI + Dockerfile) | CLOSED |
| 21 | Visual regression testing | **CLOSED** (5/5 tasks done, TASK-0057–0061) |
| 22 | Multi-step Playwright test scripts | **NEXT** (not started) |
| 23 | CI/CD integration (GitHub Actions) | pending |
| 24 | Multi-viewport testing | pending |
| 25 | Alerts + webhooks | pending |
| 26 | Multi-user + org accounts | pending |

---

## Phase 21 Delivery (Visual Regression)

All 5 tasks done:
- **P21-T01** (TASK-0057): Baseline capture — mark a packet as the approved baseline for a URL
- **P21-T02** (TASK-0058): Pixel diff engine — compare new capture against baseline, generate diff image
- **P21-T03** (TASK-0059): Diff view in dashboard — before/after slider + highlighted regions
- **P21-T04** (TASK-0060): Approve/reject workflow — accept new baseline or flag as regression
- **P21-T05** (TASK-0061): `assay run --compare` — diff against baseline from CLI, exit 1 on regression

---

## What's Next

**Phase 22 — Multi-step Playwright Test Scripts** is the logical next phase. Instead of single-URL screenshot captures, Phase 22 gives Assay the ability to run multi-step test scripts: navigate, click, fill, screenshot at each step. This is the transition from "screenshot verification tool" to "lightweight E2E test runner."

The 4 Phase 22 backlog items (seeded as task packets in P18-T04):
- Test script format (JS/TS file with steps)
- `assay run --script <file>` execution
- Script result packet with per-step screenshots
- Built-in script library helpers

**Downstream phases (pending, no task packets):**
- Phase 23 — CI/CD integration (GitHub Actions, PR comments, status checks)
- Phase 24 — Multi-viewport testing
- Phase 25 — Alerts + webhooks
- Phase 26 — Multi-user + org accounts

---

## Open Directions

From `docs/working/open_questions.md` — open or deferred:

- **Q5 — Monetization model:** Deferred to v2 planning. API key infrastructure is sufficient for now. The hosted dashboard and Phase 26 org accounts are the natural setup for paid tiers.
- **Q6 — API key storage encryption:** v1 uses bcrypt + plaintext JSON file. Keychain support deferred to v2.

From the roadmap:
- **Multi-browser support** — currently Chromium-only via Playwright. Cross-browser is a strong candidate for a future phase.
- **Public sharing** — share a verification report via a public link (SaaS feature, requires Phase 26 org model first)
- **Assay SDK for Python** — for server-side verification capture (not just browser SDK)
- **Conclave integration** — Assay as a tool a Conclave Familiar can invoke (long-term, post-toolkit contract work)

---

## Active Constraints

- `assay schedule start` uses `os.fork()` — POSIX only. No Windows support until daemon is refactored.
- Canonical docs require human approval before direct edits (standard Grain constraint).
- Multi-user accounts (Phase 26) are a prerequisite for any paid/hosted tier billing hooks.
- The Grain bridge (`grain verify ingest`) expects Assay's result payload to match the schema defined in Grain's `data_contracts.md §Sentinel bridge` — Assay must stay aligned with this contract.

---

## Stale Doc Note

`docs/working/v2_plan.md` is essentially empty — no content beyond the heading. The internal future roadmap belongs in `docs/working/roadmap.md` (seeded in P18-T03).
