# Review Active Task

You are reviewing the active task for this project.

## Step 1 — Read Files

Read:

* docs/runtime/PROJECT_RULES.md

* docs/runtime/docs_index.md

* docs/runtime/docs_manifest.yaml

* docs/runtime/context_loading.md

* docs/runtime/agent_profiles.md

* docs/working/current_focus.md

* docs/working/current_task.md

* templates/tasks/results.md

* templates/tasks/handoff.md

* templates/tasks/task_packet.md

Then read the task folder referenced in `docs/working/current_task.md`.

At minimum, read:

* task.md
* context.md
* plan.md
* deliverable_spec.md
* results.md if present
* handoff.md if present

Read the files changed for the task.

Read only the canonical docs referenced by the active task packet.

## Step 2 — Review Against Task Scope

Check:

* correctness
* consistency with canonical docs
* consistency with the task packet
* missing logic
* edge cases
* overreach beyond scope
* missing documentation updates
* missing follow-up notes
* whether deliverable_spec.md is satisfied
* whether `results.md` and `handoff.md` conform to the current task templates — note: `results.md` does NOT have a top-level `## Status` field; packet status lives only in `task.md`

**Named tool/library check (required):**
If the task description or title names a specific library or tool as the implementation approach (e.g. "use tree-sitter", "implement with NetworkX", "add redis caching"), verify that library is actually imported and called in the implementation files. A dependency declaration in `pyproject.toml` or a comment referencing the library is not sufficient. If the named tool appears in the spec but is not imported and used in the code, this is a **failing condition** — set review decision to `needs fixes` and record it as a required fix, not an optional improvement.

## Step 3 — Apply Trivial Fixes Inline (Optional)

Before recording the review decision, check whether any required fix is trivial enough to apply directly:

A fix is trivial if it meets **all** of the following:
- Self-contained change of roughly 20 lines or fewer
- No new canonical decisions or workflow semantics required
- No ambiguity about what the correct fix is
- Change touches at most 1–2 files

If a fix is trivial: apply it, run tests to confirm, update `results.md` with a note in Review Notes, and set the review decision to `ready`.

If a fix requires domain reasoning, touches multiple files, or introduces any ambiguity: do not apply it. Record it under Required Fixes and set the review decision to `needs fixes` so the executor can address it.

If all fixes were applied inline: proceed to Step 4 as if the task were already ready.

## Step 4 — Determine Status

Decide whether the task is:

* ready
* needs fixes
* blocked
* unclear due to spec conflict

## Step 5 — Classify Review Follow-Ups

Classify follow-ups explicitly so closeout can apply them without guessing from prose.

Use these buckets:

* `open_questions_to_log`
  * use only for real unresolved decisions or ambiguities that should be recorded in `docs/working/open_questions.md`
* `proposal_candidates_to_log`
  * use only for real canonical or runtime mismatches that should be recorded in `docs/working/change_proposals.md`
* `followups_to_log`
  * use for non-blocking implementation notes, next-task cautions, or handoff items that do not belong in working-layer authority docs

Do not place optional improvements or speculative ideas into `open_questions_to_log` or `proposal_candidates_to_log`.

If review shows that a backlog item was too broad or should be split, record that as a follow-up or working-doc planning note. Do not split backlog items during review.

If a bucket is empty, return `None`.

## Step 6 — Persist The Review Bundle For Closeout

Update `results.md` directly so the structured review outcome is recorded in the task artifacts.

Create or update `handoff.md` directly so closeout and the next task have a durable handoff artifact.

Follow the structure in:

* `templates/tasks/results.md`
* `templates/tasks/handoff.md`

At minimum, persist:

* user review state
* user review summary
* resolution mode
* required fixes
* open questions to log
* proposal candidates to log
* follow-ups to log
* residual risks
* verification state if a verifier was run; otherwise keep it at `not_run`
* closure decision left open unless the task is actually being closed
* efficiency Review stage filled in — prompt runs and conversation restarts for this review conversation only; do not modify Execute or Close stages

If `handoff.md` does not exist, create it.

## Output

Return ONLY:

1. issues found
2. required fixes
3. optional improvements
4. whether the task meets definition of done
5. recommended next status for the active task
6. `open_questions_to_log`
7. `proposal_candidates_to_log`
8. `followups_to_log`
9. residual risks
10. files updated
11. summary of persisted review bundle

No explanation.
