# Current Focus

## Current Phase
Phase 22 — Developer Experience + SDK Integration

---

## Active Focus

Phase 21 complete: visual regression, pixel diff engine, approve/reject workflow, `assay run --compare`.

Phase 22: remove setup friction. Goal is a 2-minute path from `pip install assay-kit` to first captured packet, and a clean SDK integration story for app projects (Vite/React, Next.js).

---

## Immediate Priorities

1. P22-T01: `assay init` — interactive wizard writes `assay.toml` + prints `.env` block
2. P22-T02: `assay key create` UX — print curl example + SDK snippet after key creation
3. P22-T03: SDK `fromEnv()` factory + `useAssayCapture()` React hook
4. P22-T04: Framework-specific setup guides in `packages/assay-sdk/docs/`

---

## Active Constraints

- Canonical docs require human approval before direct edits
- `assay schedule start` uses `os.fork()` — POSIX only (no Windows support)

Phase 15 closed: 2026-04-29 — 2 tasks done (grain-verified)

Phase 16 closed: 2026-05-05 — 5 tasks done (grain-verified)

Phase 17 closed: 2026-05-05 — 3 tasks done (grain-verified)

Phase 18 closed: 2026-05-08 — 5 tasks done (grain-verified)

Phase 19 closed: 2026-05-11 — 3 tasks done (grain-verified)

Phase 20 closed: 2026-05-12 — 5 tasks done (grain-verified)
