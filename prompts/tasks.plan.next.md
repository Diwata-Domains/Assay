# Plan Next Task Or Split Active Backlog Item

You are planning the next executable task inside the active phase.

This prompt is for task planning, not implementation.

Use it when:
- the next task should be selected before packet generation
- a backlog item is too broad and needs to be split
- a follow-up task should be created from completed work

Metadata:
- scope: task
- stage: plan_next
- recommended_model_class: frontier_model
- escalation_model_class: reviewer_model

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

Read any additional canonical docs declared in `docs/runtime/docs_manifest.yaml` only when they are relevant to sequencing or task scope.

If a recently completed or blocked task matters for sequencing, read only that task folder.

At minimum, if present, read:

* task.md
* results.md
* handoff.md

Do not read unrelated task folders.

---

## Step 2 — Identify Planning Need

Determine which of these applies:

1. select the next existing backlog item as-is
2. split one too-broad backlog item into smaller backlog items
3. add one concrete follow-up task exposed by review or closeout

Do not invent a new phase.
Do not generate a task packet yet.

---

## Step 3 — Validate Scope

Any task selected or created here must:

* belong to the active phase
* align with canonical docs
* be small enough for one future packet
* have a clear deliverable
* not depend on unresolved blocking questions

If a backlog item is too broad:

* split it in `docs/working/backlog.md`
* keep the original intent
* prefer the smallest valid executable first slice
* sequence the remaining slices explicitly

If the split would change architecture or canonical scope, stop and route that through `change_proposals.md` instead.

---

## Step 4 — Update Working Docs

Update as needed:

* docs/working/backlog.md
* docs/working/current_focus.md
* docs/working/implementation_plan.md only if sequencing language must change

Rules:

* task planning owns task generation and backlog splitting
* review and close may identify split candidates, but should not perform planning unless explicitly redirected here
* do not modify canonical docs
* do not generate a packet

---

## Step 5 — Prepare Packetization Readiness

For the chosen next task, state whether it is:

* ready for packet generation
* blocked pending a decision
* still too broad and needs human planning

If ready, identify:

* task ID or backlog label
* short objective
* dependencies
* likely files or areas affected
* recommended model class

---

## Output

Return ONLY:

1. planning action taken
2. next task selected or split created
3. working-doc files updated
4. packetization readiness
5. blockers or decisions still needed

No explanation.
