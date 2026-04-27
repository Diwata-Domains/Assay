# Review and Close Current Phase

You are reviewing and closing the current phase of this project.

This is phase-level only; do not use it for individual task review or closure.

Metadata:
- scope: phase
- stage: review_and_close
- recommended_model_class: reviewer_model

## Objective

Review the current phase as a whole, determine whether it is ready to close, update working documents to reflect the real project state, and prepare the project for the next phase or next immediate focus.

This prompt replaces separate phase review and phase close steps when the phase is closeable.

---

## Step 1 — Read Files

Read:

* docs/runtime/PROJECT_RULES.md

* docs/runtime/docs_index.md

* docs/runtime/docs_manifest.yaml

* docs/runtime/context_loading.md

* docs/runtime/agent_profiles.md

* docs/working/implementation_plan.md

* docs/working/backlog.md

* docs/working/current_focus.md

* docs/working/open_questions.md

* docs/working/change_proposals.md

* docs/working/current_task.md

* docs/working/workflow_metrics.md if present

* docs/canonical/product_scope.md

* docs/canonical/architecture.md
* any additional canonical docs from `docs/runtime/docs_manifest.yaml` that are relevant to the phase being closed

Read the task folders relevant to the current phase.

At minimum, from each relevant task folder if present, read:

* task.md
* results.md
* handoff.md

Read the implementation artifacts and changed files relevant to those tasks.

Do not read unrelated task folders or unrelated future-phase work.

---

## Step 2 — Identify the Active Phase

Determine the current phase from:

* current_focus.md
* implementation_plan.md
* backlog.md

Use the phase defined in working docs unless there is a clear inconsistency that must be reported.

---

## Step 3 — Review the Phase

Evaluate the current phase against its intended goals.

Check:

* whether the phase goals and key deliverables were actually completed
* whether completed tasks align with canonical docs
* whether implementation introduced drift from architecture or workflow rules
* whether completed work is coherent as a phase, not just as isolated tasks
* whether important tasks remain unfinished
* whether unresolved blockers or open questions still prevent closure
* whether any canonical mismatch should become or remain a change proposal
* whether working docs still reflect reality

Group findings into:

### Completed Correctly

* work completed and aligned with source-of-truth

### Issues Preventing Closure

* incomplete work
* incorrect implementation
* unresolved blockers
* open questions still blocking closure
* documentation gaps
* sequencing problems

### Canonical Drift or Proposal Candidates

* any places where implementation suggests a needed canonical change proposal
* do not modify canonical docs directly

---

## Step 4 — Classify System Improvements

Identify system-level improvements exposed by this phase.

Use only these buckets:

### Fix Now

* workflow bugs or drift that will likely harm the next task or next phase if left unresolved

### Batch Next Phase

* repeated friction
* validator ideas
* prompt or template cleanup
* metrics or ergonomics improvements that are worthwhile but not urgent

### Ignore

* one-off noise
* issues not worth system change

Rules:

* prefer repeated evidence over isolated annoyance
* do not create backlog items unless the work is already concrete and scoped
* route unresolved decisions to `open_questions.md`
* route canonical or runtime authority gaps to `change_proposals.md`

---

## Step 5 — Determine Closure Eligibility

A phase is ready to close only if:

* its key planned deliverables are complete
* major blockers are resolved or explicitly deferred without breaking phase intent
* remaining unfinished tasks are either intentionally moved forward, deferred, or clearly recorded
* no unresolved blocking open question prevents closure
* working docs can be updated without hiding issues

If the phase is not ready to close:

* do not mark it closed
* return the reasons
* return the updates needed for working docs
* return the recommended status of the phase

If the phase is ready to close:

* proceed with closeout updates

---

## Step 6 — Update Working Docs

Generate updated contents or targeted patch-style updates for:

* docs/working/implementation_plan.md
* docs/working/backlog.md
* docs/working/current_focus.md
* docs/working/open_questions.md
* docs/working/change_proposals.md
* docs/working/current_task.md
* docs/working/workflow_metrics.md if present

### Update rules

#### implementation_plan.md

* reflect completed phase status
* identify the next phase or next immediate milestone
* preserve lightweight sequencing

#### backlog.md

* mark completed tasks appropriately
* keep unresolved tasks if they still matter
* move deferred or carryover work to the correct place
* do not invent major new work unless clearly implied by implementation reality

#### current_focus.md

* if the phase closes, shift to the next active phase or immediate next focus
* if the phase does not close, keep focus on what remains
* keep concise and actionable

#### open_questions.md

* remove or update resolved questions
* keep unresolved questions that still matter
* update statuses if a question moved from blocking to resolved, deferred, or escalated

#### change_proposals.md

* add or update proposal entries only if implementation revealed real canonical mismatch
* do not modify canonical docs directly

#### current_task.md

* if the phase closes and no specific task remains active, set:

# Current Task

Task ID: none
Task Path: none
Status: unset

* if a carryover task remains active, reflect that explicitly

#### workflow_metrics.md

* update phase metrics if enough information exists
* preserve prior phase metrics
* do not fabricate unknown values
* if exact values are not known, keep existing values or mark them clearly as approximate
* add a short system-improvement note for:
  * fix now
  * batch next phase
  * ignore

---

## Step 7 — Phase Close Summary

Generate a concise summary including:

* phase reviewed
* whether phase is closed
* what was completed
* what remains or carries over
* whether any change proposals were created or updated
* what the project should do next

---

## Step 8 — Next-Step Readiness

Determine one of:

* ready for next task in the next phase
* ready for next phase planning
* phase not ready to close; continue current phase
* human review required before continuing

---

## Constraints

* DO NOT generate code
* DO NOT generate the next task packet
* DO NOT modify canonical docs directly
* DO NOT close the phase if meaningful blocking issues remain
* DO NOT hide unresolved issues
* DO NOT rewrite unrelated working docs unnecessarily

---

## Output

Return ONLY:

1. current phase identified
2. completed correctly
3. issues preventing closure, if any
4. canonical drift or proposal candidates
5. system improvements:
   * fix_now
   * batch_next_phase
   * ignore
6. phase closure decision
7. updated contents or targeted updates for working docs
8. phase close summary
9. next-step readiness

No explanation.
