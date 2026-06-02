# Task: Script result packet — per-step screenshots + pass/fail per step

## Metadata
- **ID:** TASK-0064
- **Status:** pending
- **Phase:** Phase 22 — Multi-step Playwright Test Scripts
- **Backlog:** P22-T03
- **Packet Path:** tasks/P22-T03-TASK-0064/
- **Dependencies:** TASK-0063
- **Primary Adapter:** code

## Objective
Extend the verification result packet format to represent multi-step script results. Each step has its own outcome, screenshot reference, and timing. The packet must remain compatible with the Grain bridge contract.

## Why This Task Exists
`assay run --script` (P22-T02) produces per-step screenshots but needs a structured output packet that represents the full script run — not just a single screenshot. The existing packet format (designed for single-URL captures) needs extension for multi-step results.

## Scope
- Extend the result packet JSON schema to include a `steps` array:
  - Each step: `step_index`, `step_type`, `step_name`, `outcome` (pass/fail/skip), `screenshot_ref` (nullable), `error` (nullable), `duration_ms`
- Overall packet outcome: `pass` if all steps pass; `fail` if any step fails; `error` if execution crashed
- Update `assay run --script` to write a result packet with the `steps` array on completion
- Update `assay report` to display multi-step packets: show step list, per-step pass/fail, inline screenshot per step
- Update dashboard packet detail view to render the step list for script-run packets
- Verify Grain bridge contract compatibility: the top-level `outcome`, `verification_id`, `task_id`, `severity`, `summary` fields must remain present and correct
- Tests: packet schema validates, `assay report` renders step list, dashboard step view renders correctly

## Deliverable
Result packet format supports `steps` array. `assay report` and dashboard display per-step results. Grain bridge fields remain valid. Tests passing.

## Constraints
- The `steps` field must be optional (absent on single-URL screenshot packets) — backward compatible
- The Grain bridge contract schema must not change — only additive fields allowed
- `summary` field in the packet should summarize the script result: e.g. "3/4 steps passed, step 'submit_form' failed"
