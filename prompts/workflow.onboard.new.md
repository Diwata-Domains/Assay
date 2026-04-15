# New-Project Onboarding Prompt

Use this as the stable onboarding entrypoint for brand-new projects.

Metadata:
- scope: project
- stage: onboard_new
- recommended_model_class: frontier_model
- escalation_model_class: frontier_model

You are onboarding a new project into Grain.

---

## Scope Boundary

This prompt is only for new-project onboarding.

Do not implement existing-project repo scanning or adoption behavior here.

---

## Run Mode

1. Ask questions first.
2. Wait for answers.
3. Generate onboarding outputs only after answers are complete.
4. If information is missing, ask focused follow-up questions before generating files.

Do not guess through unresolved constraints.

---

## Project Intake (Fill Before Running)

<!-- Replace all placeholder values before running -->

**Project Name:** [Your project name]

**Project Type:** [New project only]

**Purpose:**
[What this project does and why it exists. 2–4 specific sentences.]

**Target User:**
[Who uses this system and in what context.]

**Key Capabilities:**
[Bullet list of core features/outcomes.]

**Tech Stack:**
[Languages, frameworks, platforms, and key tools.]

**Constraints:**
[Operational, scope, and architecture constraints.]

**v1 Scope Boundaries:**
[What is in scope now and explicitly out of scope.]

**Primary Adapter (required):**
[e.g. code_adapter]

**Secondary Adapters (optional):**
[comma-separated adapter IDs or `none`]

**Starter Packet Bootstrap (optional):**
[yes/no; default no]

**Known Open Questions:**
[Unresolved decisions to seed into `open_questions.md`, or `none`]

---

## Required Behavior

- Keep onboarding agent-first and question-driven.
- Keep provider handling model-agnostic in this slice.
- Keep outputs additive and locally inspectable.
- Put unresolved decisions in `docs/working/open_questions.md` with explicit status.
- Keep existing-project adoption deferred; do not blend modes.

---

## Required Output

### 1. Documentation System Draft
Generate initial:
- canonical docs
- working docs
- runtime docs
- task packet scaffolding

For each, include:
- purpose
- authority
- edit permissions

### 2. `docs/runtime/docs_manifest.yaml`
Generate a full manifest with:
- `canonical`
- `working`
- `runtime`
- `tasks`
- `rules`

Include selected adapter entries and keep schema compatible with existing Grain contracts.

### 3. `docs/runtime/docs_index.md`
Generate the human-readable index from the manifest structure:
- hierarchy
- read order
- edit permissions

### 4. `docs/runtime/PROJECT_RULES.md`
Generate execution/authority/context/completion rules aligned with Grain workflow.

### 5. `docs/runtime/agent_profiles.md`
Generate model-class guidance for:
- `open_model`
- `frontier_model`
- `reviewer_model`

### 6. `docs/working/implementation_plan.md`
Generate a phased plan grounded in stated scope and constraints.

### 7. `docs/working/backlog.md`
Generate concrete starter tasks grouped by phase.

### 8. `docs/working/open_questions.md`
Record unresolved items as structured open questions with status.

### 9. Prompt/Workflow Surface Notes
Summarize which stable prompts to run next after onboarding.

### 10. Optional Starter Packet
If `Starter Packet Bootstrap` is `yes`, generate one small starter packet proposal; otherwise skip.

---

## Goal

Produce onboarding outputs that are immediately usable as draft repo state, while preserving explicit review before treating canonical content as fully approved.
