# Current Task

Status: **ready** — task packet active.

- **Task ID:** TASK-0077
- **Task:** Assay Ironvale Dashboard SPA (Phase 28 — P28-T05)
- **Task Path:** tasks/P28-T05-TASK-0077/
- **Status:** ready

Replace the inline-HTML dashboard (`/`, `/packet/{id}`) with a session-authed JSON REST API
(`/api/packets*`) + a React + Ironvale SPA in `apps/assay-dashboard` served at `/dashboard`.
Same Warden session login as the existing HTML dashboard (NOT API-key, NOT `public_prefixes`).

> **ID note:** this task reuses `TASK-0077`, which was already minted by the closed Phase 29
> packet (`tasks/P29-agent-surface-TASK-0077/`). The archive max is TASK-0076 and the
> next free derived ID is TASK-0078, but the dashboard work order pins `TASK-0077`; the
> directory `P28-T05-TASK-0077` namespaces it so the P29 packet is not overwritten. Collision
> logged in `docs/working/tooling_notes.md`.

Last closed: **TASK-0077 — Phase 29 Agent-Usable Verification Surface** (done 2026-06-25,
`tasks/P29-agent-surface-TASK-0077/`). The authoritative active phase is **Phase 28 — Release
v0.3.0 + Documentation Reconciliation** (see `docs/working/current_focus.md`). Phase task state
lives in `docs/working/backlog.md`.

When the next task is opened, set:
- Task ID: TASK-XXXX (next NEW id is TASK-0078 — derive from the `tasks/archive/` max, see `CLAUDE.md`)
- Task Path: tasks/P{phase}-TNN-TASK-XXXX/
- Status: ready | in_progress
