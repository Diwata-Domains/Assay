# Generate Next Task Packet and Implement It

Use this as the default executor-start prompt.

You are selecting the next appropriate task, generating its task packet, setting it as the active task, and implementing it.

## Objective

Perform the next executable unit of work for the current phase with minimal workflow overhead.

This includes:

1. selecting the next valid task from backlog
2. generating the task packet
3. updating `docs/working/current_task.md`
4. implementing the task
5. updating task artifacts with results

Do not perform review or phase closeout in this prompt.

Small fixes and hotfixes still use normal task packets. Do not bypass packet creation just because the change is small.

If `docs/working/current_task.md` already points to an active task:

* continue that task if its status is `in_progress` or `blocked`
* do not select a new backlog task if the current task is still active
* stop and hand off to review if the current task is already at `review`

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

* docs/working/current_task.md

* docs/working/open_questions.md

* docs/working/change_proposals.md

* docs/canonical/product_scope.md

* docs/canonical/architecture.md

Read any additional canonical docs declared in `docs/runtime/docs_manifest.yaml` only if they are relevant to the task being executed.

* templates/tasks/task_packet.md
* templates/tasks/task.md
* templates/tasks/context.md
* templates/tasks/plan.md
* templates/tasks/deliverable_spec.md
* templates/tasks/results.md
* templates/tasks/handoff.md

If `docs/working/current_task.md` points to an existing task, read that task only as needed to understand what was just completed.

At minimum, if present, read:

* task.md
* results.md
* handoff.md

Do not read unrelated task folders.

---

## Step 2 — Select the Next Task

If there is no active task to continue, choose ONE task from backlog.md that:

* belongs to the current phase
* is not completed
* is concrete and implementable
* is small enough for a single task packet
* is not blocked by an unresolved open question
* logically follows completed work
* helps unblock future work

If a task is blocked by an open question, do not choose it unless the question is already resolved in project docs.

If multiple tasks qualify, choose the simplest valid next task.

Do NOT:

* combine multiple tasks
* invent a new backlog task
* skip ahead to future phases
* select work that depends on unresolved prerequisites

---

## Step 3 — Validate Before Packet Generation

Confirm that the selected task:

* aligns with canonical docs
* fits the current phase
* does not require redefining architecture or scope
* has a clear deliverable
* can be implemented without first resolving a blocking question

If the selected task cannot be safely executed, stop and return the reason.

If the next backlog item is too broad for one packet, do not split it inside execution. Stop and route task planning through `prompts/task.plan.next.md` first.

---

## Step 4 — Generate the Task Packet

Using `templates/tasks/task_packet.md`, generate the completed task packet for the selected task.

Keep it:

* narrow
* executable
* minimal
* consistent with project rules

List only likely files to change.

Do not generate unnecessary narrative.

---

## Step 5 — Set the Active Task

Generate updated contents for:

`docs/working/current_task.md`

Use this format exactly:

# Current Task

Task ID: [TASK-ID]
Task Path: tasks/[TASK-ID]/
Status: in_progress

---

## Step 6 — Implement the Task

Implement the generated active task.

Rules:

* follow the generated task packet strictly
* do not expand scope
* do not modify unrelated files
* preserve project structure and conventions
* prefer minimal, targeted edits
* do not modify canonical docs directly

If implementation reveals a blocking ambiguity or unresolved open question, stop and record it rather than improvising.

---

## Step 7 — Update Task Artifacts

Generate or update task artifacts as appropriate.

Follow the structure in:

* `templates/tasks/task.md`
* `templates/tasks/context.md`
* `templates/tasks/plan.md`
* `templates/tasks/deliverable_spec.md`
* `templates/tasks/results.md`
* `templates/tasks/handoff.md`

At minimum, generate updated contents for:

* `task.md`
* `context.md`
* `plan.md`
* `deliverable_spec.md`
* `results.md`
* `handoff.md` if the task is moving to `review`

Include in `results.md`:

* summary of work completed
* files changed
* tests run or validation performed
* efficiency metrics for the Execute stage only — do not fill in Review or Close:
  * prompt runs for this conversation
  * conversation restarts
  * files read estimated
  * notes on where cost was high or low
* Review Notes — facts and tradeoffs a reviewer should inspect
* blockers encountered
* unresolved follow-up items

Do NOT fill in the `User Review`, `Verification Review`, or `Closure Decision` sections. The reviewer, verifier, and closer own those sections.

Include in `handoff.md`:

* packet identity and phase
* current task status
* recommended next status
* short summary of what was built
* what review should check
* known issues or follow-ups
* files changed

If the task is moving to `review`, `handoff.md` is required.

---

## Step 8 — Determine Completion State

At the end, determine whether the task is:

* ready for phase-level review later
* blocked
* still in progress

Update `docs/working/current_task.md` accordingly.

Use one of:

* `in_progress`
* `blocked`
* `review`

If implementation completed the task successfully, prefer:

* `review`

Do not move a task to `review` unless `results.md` and `handoff.md` are both updated for reviewer handoff.

Do not set:

* `done`

Task completion should be finalized during your broader review/close workflow.

---

## Model Selection

Use:

* `open_model` only if the selected task is narrow and mechanical
* `frontier_model` if the task affects structure, CLI behavior, coordination, or has ambiguity
* `reviewer_model` is not used in this prompt, but should be considered later during phase review

Include short reasoning in the task packet.

---

## Constraints

* DO NOT generate multiple task packets
* DO NOT generate review or phase-close output
* DO NOT modify canonical docs directly
* DO NOT hide blockers
* DO NOT proceed past a genuinely blocked task
* DO NOT invent new architecture

---

## Output

Return ONLY:

1. completed task packet
2. updated contents for `docs/working/current_task.md`
3. implementation summary
4. updated contents for task artifact files

If you continued an existing task, state that briefly in the implementation summary.

No explanation.
