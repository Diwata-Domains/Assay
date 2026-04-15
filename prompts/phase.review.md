# Review Current Phase

Review the current phase for closure readiness without rewriting the working docs.

Metadata:
- scope: phase
- stage: review
- recommended_model_class: reviewer_model

---

## Objective

Assess whether the current phase is complete enough to close, whether any drift remains, and what should happen next.

---

## Step 1 - Read Files

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
* docs/canonical/product_scope.md
* docs/canonical/architecture.md

Read any additional canonical docs declared in `docs/runtime/docs_manifest.yaml` only when they are relevant to the phase under review.

Read the task folders relevant to the current phase.

At minimum, from each relevant task folder if present, read:

* task.md
* results.md
* handoff.md

Read the implementation artifacts and changed files relevant to those tasks.

---

## Step 2 - Review the Phase

Evaluate:

* completed work
* unfinished work
* unresolved blockers
* open questions
* canonical drift or proposal candidates
* whether the working docs still reflect reality

Do not modify files directly.

Do not redefine scope or architecture.

If implementation conflicts with canonical docs, record it as a proposal candidate or unresolved issue.

---

## Step 3 - Decide Closure Readiness

A phase is ready to close only if:

* key deliverables are complete
* blockers are resolved or intentionally deferred
* unfinished work is explicitly carried forward
* no unresolved blocking question remains

If the phase is not ready, say so clearly and identify what remains.

---

## Step 4 - Classify System Improvements

Identify system-level improvements exposed by the phase.

Use only these buckets:

* `fix_now`
  * use for workflow bugs or drift that will likely harm the next task if left uncorrected
* `batch_next_phase`
  * use for repeated friction, validator ideas, prompt cleanup, or ergonomic improvements that are real but not urgent
* `ignore`
  * use for one-off noise or issues not worth system change

Rules:

* prefer concrete workflow failures over general opinions
* do not create backlog items from this step unless the work is already concrete and scoped
* route unresolved design decisions to `open_questions.md`
* route canonical or runtime authority gaps to `change_proposals.md`

---

## Constraints

* do not generate code
* do not generate the next task packet
* do not modify canonical docs directly
* do not hide unresolved issues

---

## Output

Return ONLY:

1. current phase identified
2. completed correctly
3. issues preventing closure
4. canonical drift or proposal candidates
5. system improvements:
   * fix_now
   * batch_next_phase
   * ignore
6. closure readiness

No explanation.
