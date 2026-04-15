# Existing-Project Onboarding Prompt

Use this as the stable onboarding entrypoint for adopting an existing repository into Grain.

Metadata:
- scope: project
- stage: onboard_existing
- recommended_model_class: frontier_model
- escalation_model_class: frontier_model

You are onboarding an existing project into Grain.

---

## Scope Boundary

This prompt is only for existing-project adoption.

Do not use it for brand-new project initialization.

---

## Run Mode

1. Inspect first, then ask focused questions.
2. Require mandatory CLI steps before writing or revising docs.
3. Keep all generated content explicitly marked draft until a human confirms it.
4. If key context is missing, ask targeted follow-up questions instead of guessing.

---

## Required Inputs (Fill Before Running)

<!-- Replace all placeholder values before running -->

**Repository Root Path:** [absolute or relative repo path]

**Project Purpose (known):**
[What this project is for, if known.]

**Known Constraints:**
[Deployment, security, compliance, runtime, or team constraints.]

**Primary Maintainer Notes (optional):**
[Any existing conventions or boundaries to preserve.]

---

## Mandatory CLI Steps

Run these commands exactly in this order.

1. Scaffold additively into the existing repo:

```bash
grain --repo <REPO_ROOT> onboard <REPO_ROOT> --format json
```

2. Verify docs/runtime contracts are still valid:

```bash
grain --repo <REPO_ROOT> docs validate
```

3. Verify workflow state and next legal action:

```bash
grain --repo <REPO_ROOT> --format json workflow next
```

4. If a task packet is generated or selected during this flow, validate it:

```bash
grain --repo <REPO_ROOT> task validate --id <TASK-ID>
```

Do not skip these steps. If any command fails, stop and report the failure with actionable next steps.

---

## Required Behavior

- Keep the flow additive-only; never overwrite existing files silently.
- Treat scan and generated outputs as draft proposals, not canonical truth.
- Review generated stubs and scan-derived assumptions before expanding docs.
- Ask targeted clarifying questions for missing architecture, workflow, or validation details.
- Record unresolved decisions in `docs/working/open_questions.md`.
- Record structural/canonical drift candidates in `docs/working/change_proposals.md`.

---

## Execution Sequence

### 1) Scaffold and Baseline Validation
- Run the mandatory CLI steps.
- Summarize what was created vs skipped from onboard output.
- Confirm whether docs validation passed.

### 2) Scan and Signal Review
- Review detected signals (languages, adapters, key files, CI, docs).
- Identify confidence gaps and assumptions requiring maintainer confirmation.
- Do not claim certainty when signals are ambiguous.

### 3) Clarifying Questions
Ask concise, high-value questions such as:
- What is the product boundary and intended users?
- What architecture constraints are non-negotiable?
- What test/verification commands are mandatory before merge?
- Which adapters should be primary vs secondary for this repo?

### 4) Draft Canonical + Working Docs
Fill or revise draft docs using confirmed information:
- `docs/canonical/product_scope.md`
- `docs/canonical/architecture.md`
- `docs/working/backlog.md`
- `docs/working/open_questions.md`

Rules:
- Preserve `# DRAFT` markers until human review is complete.
- Keep outputs specific, inspectable, and grounded in repo evidence.

### 5) Record Remaining Gaps
- Add unresolved items to `open_questions.md` with explicit status.
- If gaps imply canonical policy changes, add proposal entries to `change_proposals.md`.

---

## Required Output

Return:
1. command results summary (onboard, docs validate, workflow next, task validate if run)
2. created/skipped scaffold summary
3. confirmed project facts vs assumptions
4. clarifying questions asked (and answers, if provided)
5. files drafted/updated
6. remaining open questions and proposal candidates

---

## Goal

Produce a usable first-pass draft adoption state for an existing repository in one pass, while preserving explicit review gates and human authority over canonical truth.
