# Plan Next Phase

Plan the next phase or transition slice without starting implementation.

Metadata:
- scope: phase
- stage: plan_next
- recommended_model_class: frontier_model
- escalation_model_class: reviewer_model

## Objective

Define the next coherent phase after the current completed phase or transition state.

This is for medium-horizon planning, not task packet generation.

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
* docs/working/future_roadmap.md
* docs/working/v2_plan.md if present
* docs/working/v2_adapters.md if present
* docs/working/v2_onboarding.md if present
* docs/canonical/product_scope.md
* docs/canonical/architecture.md

Read any additional canonical docs declared in `docs/runtime/docs_manifest.yaml` only when they materially affect phase planning.

Read only the task folders needed to understand the just-completed phase or transition state.

---

## Step 2 — Identify The Next Planning Horizon

Determine:

* whether the next step should be a full new phase or a transition slice
* which roadmap items are dependency-ready
* which planning docs already constrain the next phase

Do not overplan distant future phases.
Prefer one active next phase and, at most, one coarse follow-on phase.

---

## Step 3 — Draft The Next Phase

For the next phase, define:

* phase name
* objective
* major deliverables
* output focus
* dependencies
* sequencing notes

Then create or update the corresponding backlog slice with concrete candidate tasks.

Rules:

* keep the phase coherent
* keep deliverables scannable
* do not create implementation packets yet
* do not silently change canonical scope

---

## Step 4 — Update Working Docs

Update as needed:

* docs/working/implementation_plan.md
* docs/working/backlog.md
* docs/working/current_focus.md
* docs/working/v2_plan.md if present

Do not modify canonical docs.

---

## Output

Return ONLY:

1. next phase or transition identified
2. why it is the right next horizon
3. working-doc files updated
4. candidate backlog slice created
5. blockers or decisions still needed before implementation

No explanation.
