# Close Reviewed Task

Use this after a task has already been reviewed and accepted.

You are finalizing one reviewed task packet so the workflow can move on cleanly.

---

## Step 1 — Read Files

Read:

* docs/runtime/PROJECT_RULES.md
* docs/runtime/docs_index.md
* docs/runtime/docs_manifest.yaml
* docs/runtime/context_loading.md
* docs/runtime/agent_profiles.md
* docs/working/current_task.md
* docs/working/current_focus.md
* docs/working/backlog.md

* templates/tasks/results.md
* templates/tasks/handoff.md
* templates/tasks/task_packet.md

Then read the active task folder referenced by `docs/working/current_task.md`.

At minimum, read:

* task.md
* deliverable_spec.md
* results.md
* handoff.md if present

Read and update as needed:

* docs/working/open_questions.md
* docs/working/change_proposals.md

Read the changed files for the task if needed to confirm final state.

---

## Step 2 — Confirm Closure Readiness

Confirm that:

* the task is already at review or otherwise review-ready
* the review bundle is complete
* `results.md` contains an explicit review bundle with user review, verification review, and closure decision fields
* `results.md` and `handoff.md` conform to the current task templates
* `results.md` includes the per-stage efficiency section — Execute and Review stages should already be filled by prior agents; Close stage is filled by this agent now
* the deliverable_spec is satisfied
* no blocker remains
* no unresolved follow-up prevents closure
* any `open_questions_to_log` and `proposal_candidates_to_log` are explicit enough to apply safely
* if follow-ups, open questions, proposal candidates, or reviewer notes exist, `handoff.md` is present

If anything is still missing, stop and report that the task should stay at review.

---

## Step 3 — Apply Review-Driven Working-Doc Updates

Before closing the task:

* append or update `docs/working/open_questions.md` for each item under `open_questions_to_log`
* append or update `docs/working/change_proposals.md` for each item under `proposal_candidates_to_log`
* record `followups_to_log` in `handoff.md` if they are not already captured

Use these templates as the required structure:

* `templates/tasks/results.md`
* `templates/tasks/handoff.md`
* `templates/tasks/task_packet.md`

Rules:

* only apply items that are explicitly labeled in the review bundle
* do not infer new open questions or proposals from narrative prose alone
* if a labeled item is too vague to apply safely, stop and report that the task should stay at review until the review bundle is clarified
* use `decision_needed` for newly logged open questions unless another status is explicit
* create draft-style proposal entries unless the review bundle explicitly says an existing proposal should be updated
* do not split or generate backlog tasks during close; if planning work is needed, route it to `prompts/task.plan.next.md`

---

## Step 4 — Close the Task

If the task is ready to close:

* finalize the packet status to `done`
* update `docs/working/current_task.md` to:

  # Current Task

  Task ID: none
  Task Path: none
  Status: unset

* update `results.md` and `handoff.md` if they still need final status or closure notes
* set `Closure Decision` in `results.md` to `closed` with a concrete closure reason
* fill in the Close stage of the efficiency section in `results.md` — prompt runs and conversation restarts for this close conversation only
* update `docs/working/backlog.md`: find the entry matching this task's backlog ID and set its status to `done`

Do not start the next task.

---

## Step 5 — Validate the Closeout

Check that the closed task now has:

* a final `done` packet state
* a complete review bundle
* any labeled open questions and proposal candidates recorded in the appropriate working docs
* no remaining blocker
* no active current task pointer
* backlog entry for this task is marked `done`
* no prompt or runtime workflow files were modified unless the active task explicitly targeted workflow docs

---

## Constraints

* do not generate code
* do not reopen scope
* do not select a new backlog task
* do not modify canonical docs directly
* do not modify prompts or runtime workflow docs unless the active task explicitly targets workflow infrastructure
* do not close if review is incomplete

---

## Output

Return ONLY:

1. closure decision
2. files updated
3. remaining blockers or follow-ups
4. next workflow step
5. open questions logged or updated
6. change proposals logged or updated

No explanation.
