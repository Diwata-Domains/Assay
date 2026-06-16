# Task: assay run --script <file>: execute script in Docker runner

## Metadata
- **ID:** TASK-0063
- **Status:** pending
- **Phase:** Phase 22 — Multi-step Playwright Test Scripts
- **Backlog:** P22-T02
- **Packet Path:** tasks/P22-T02-TASK-0063/
- **Dependencies:** TASK-0062
- **Primary Adapter:** code

## Objective
Add `assay run --script <file>` support: parse the script file, execute each step in the Playwright Docker runner, capture screenshots at named screenshot steps, and produce a multi-step result artifact.

## Why This Task Exists
The script format exists (P22-T01) but cannot be executed yet. This task wires the script parser output into the Docker runner's Playwright session, executes steps in order, and captures outputs per step.

## Scope
- Add `--script <file>` flag to `assay run`
- Validate the script file before execution (call the parser from P22-T01; fail fast with structured error if invalid)
- Implement step execution in the Docker Playwright runner:
  - `navigate` → `page.goto(url)`
  - `click` → `page.click(selector)`
  - `fill` → `page.fill(selector, value)`
  - `screenshot` → `page.screenshot()` captured and named per step
  - `wait` → `page.waitForTimeout(ms)`
  - `waitForSelector` → `page.waitForSelector(selector)`
- Capture per-step screenshots to disk with consistent naming (`{script_name}_{step_index}_{step_name}.png`)
- On step failure: record which step failed, capture a failure screenshot, stop execution, surface structured error
- Tests: script executes successfully (mocked runner), step failure captured correctly, output naming is correct

## Deliverable
`assay run --script <file>` executes the script, produces per-step screenshots, exits 0 on success and 1 on step failure. Tests passing.

## Constraints
- `--script` and the existing URL positional argument must be mutually exclusive — one or the other, not both
- Script execution must run inside the same Docker Playwright runner as standard `assay run`
- Per-step screenshots must be stored in the same output directory as existing `assay run` screenshots
- A script with 0 screenshot steps is valid (for pure navigation/interaction scripts), but it produces no artifacts
