# Tooling Notes

Lightweight inbox for workflow friction, tool bugs, or observations noticed mid-session.
Agents write here; user reviews and escalates to the appropriate tracker.


| Date       | Command                   | Observation                                                                                                                                                                                           | Severity |
| ---------- | ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| 2026-04-15 | `grain task prepare`      | Does not detect stub packet files — reports `ok` with `missing_inputs: 0` even when context.md, plan.md, deliverable_spec.md are all unedited template stubs. **Fixed in patch.**                     | high     |
| 2026-04-15 | `grain task create`       | No lightweight packet mode — always generates a full 7-file packet even for small mechanical tasks. `--simple` flag (task.md + results.md only) would reduce overhead.                                | low      |
| 2026-04-15 | `prompts/task.execute.md` | Execute prompt is fragile in a live AI session — AI skips packet generation steps when asked to execute inline. `grain task prepare` now warns; partially addressed in patch.                         | medium   |
| 2026-04-15 | `grain upgrade`           | Does not seed new working docs defined in source manifest that are absent in the project (e.g. tooling_notes.md). Should detect and offer to seed missing working docs rather than silently skipping. | low      |
| 2026-04-15 | `grain workflow next`     | Phase review/close is a `stop_reason` but not a hard gate — bypassable by manually updating `current_focus.md`. Should require an explicit `grain phase close` command before routing to the next phase. | medium   |
| 2026-04-15 | `grain workflow next`     | At Phase 3 start, reported `phase_boundary_review_close_required` immediately because no task packets existed yet — indistinguishable from a completed phase awaiting close. Confirmed instance of GB-005. | medium   |
| 2026-04-16 | `data_contracts.md §1`    | Schema heading says "Grain Sentinel Result Payload" and references `grain verify ingest --payload <path>`. Both are stale: "Sentinel" was the internal Grain name for this tool before it became the standalone Assay app. `grain verify` does not exist in current Grain. Rename to "Assay Result Payload" and update delivery model. Change proposal CP-002 filed. | low      |
| 2026-04-20 | `grain workflow next`     | After all phase tasks closed via `grain task close --quick`, `workflow next` routes to `task_execute` for the last done task instead of advancing to the phase boundary. Root cause: `current_task.md` still points to the completed task; grain reads it as active rather than checking task status. Workaround: manually clear `current_task.md` to `none/unset`. Expected behaviour: `workflow next` should recognise a `done` task in `current_task.md` and route to phase boundary automatically. | medium   |
| 2026-04-20 | `grain workflow next`     | Phase 6 start triggered `phase_boundary_review_close_required` with "no executable tasks remain" even though Phase 6 backlog entries existed. Grain requires a task packet folder (`tasks/P6-T0N-TASK-XXXX/`) in `ready` status before routing to `task_execute` — backlog entries alone are not sufficient. Workaround: `grain task create` + `grain task status --status ready` + set `current_task.md`. Expected: seeding prompt or `grain phase start` command to handle this transition. | medium   |



| 2026-04-21 | `grain workflow next`     | After all Phase 7/8/9 tasks were closed, each phase transition triggered `phase_boundary_review_close_required` with no way to formally close a phase — `grain phase close` does not exist. The only unblock is seeding the first task of the next phase via `grain task create`, setting it to `ready`, and manually updating `current_task.md`. This repeated at every phase boundary (Phase 7→8, 8→9). The `prompts/phase.review_and_close.md` prompt covers the review logic but there is no corresponding CLI command to execute the close. Suggested fix: `grain phase close --phase N` command that validates review criteria and advances the state. | medium   |
| 2026-04-22 | AI session resume         | When a session resumes from a context summary (context window exhausted), the AI skipped creating Grain task packets for all 14 tasks across Phases 10–13 and went straight to implementation. Root cause: the summary said "immediate next step is to start Phase 10 implementation" and the AI followed that without pausing to create packets first. Task packets were created retroactively after the user flagged the gap. Suggested fix: add a standing instruction in `CLAUDE.md` or the system prompt to always create a task packet before beginning any task, regardless of how the session was initiated. | medium   |
| 2026-04-22 | `assay submit`            | Assay can submit packets to `[grain].output_path` but Grain has no command to consume them. `grain verify ingest --payload <path>` was planned in `grain/docs/working/v2_plan.md §11.2` but was never implemented because the feature became the standalone Assay tool. The submitted packets currently sit unread in the output directory. **Grain needs a command to ingest Assay packets** — suggested: `grain verify ingest --payload <path>` or `grain assay ingest --payload <path>` that reads the packet, validates required fields, and creates or links a verification record against the referenced `task_id`. | high     |

---

## 2026-04-21 — Grain has no "project complete" terminal state

**Observed:** After all 9 phases were completed and `current_focus.md` was updated to `v0.1.0 Complete`, `grain workflow next` returned `required_docs_invalid` — "unable to parse current phase from docs/working/current_focus.md".

**Root cause:** Grain's phase parser expects a phase number (e.g. "Phase 9") in `current_focus.md`. It has no terminal/done state for a completed project.

**Workaround:** Kept phase as "Phase 9" with "(complete)" suffix, which Grain can parse.

**Suggested fix:** Add a recognized terminal state (e.g. `Phase: complete` or `Phase: done`) that Grain treats as a valid no-op stop, rather than an error.

---

## 2026-06-26 — TASK-0077 ID reused across two packets (dashboard SPA vs. P29 agent-surface)

**Observed:** Opening the Phase 28 "Assay dashboard SPA" packet, the work order pinned the ID
`TASK-0077`. But `TASK-0077` was already minted by the closed Phase 29 packet
(`tasks/P29-agent-surface-TASK-0077/`), and the derived next-free ID is TASK-0078 (the
`tasks/archive/` global max is TASK-0076; `current_task.md` already says "next is TASK-0078").
So two distinct packets now carry `TASK-0077`.

**Root cause:** The next-ID rule in `CLAUDE.md` derives from the **archive** max, but TASK-0077
was consumed by a packet that is `done` yet still lives outside `tasks/archive/` (in
`tasks/P29-agent-surface-TASK-0077/`), so the archive-max derivation does not see it. An ID can
be live without being archived, and the counter misses it.

**Workaround:** Kept the work order's `TASK-0077` for the dashboard packet but namespaced the
directory as `tasks/P28-T05-TASK-0077/` so it does not overwrite the P29 packet; flagged the
reuse in `task.md`, `results.md`, `current_task.md`, and this log.

**Suggested fix:** Derive the next ID from the max across BOTH `tasks/archive/` and the live
`tasks/` packets (not the archive alone), and have `grain task create` reject an ID that already
exists in either location. Severity: medium (collision is contained by the dir namespacing, but
the counter rule is demonstrably unsound for done-but-unarchived packets).
