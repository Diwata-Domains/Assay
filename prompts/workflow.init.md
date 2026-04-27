# Workflow Initialization Prompt (Compatibility Alias)

Deprecated compatibility entrypoint.
Prefer `prompts/workflow.onboard.new.md` for new-project onboarding.

It wraps `prompts/workflow.onboard.new.md`.

Metadata:
- scope: project
- stage: initialize
- recommended_model_class: frontier_model
- escalation_model_class: frontier_model

## Purpose

Provide a stable bridge for users who still invoke `workflow.init`.

## How To Use

- For new projects: use `prompts/workflow.onboard.new.md` directly.
- For existing projects: this file remains a temporary compatibility fallback until a dedicated existing-project onboarding prompt is shipped.

## Rules

- keep onboarding question-first
- require explicit adapter selection input
- keep provider handling model-agnostic in this slice
- keep existing-project adoption flow deferred for now

## Output

Use the same output contract as `prompts/workflow.onboard.new.md`.
