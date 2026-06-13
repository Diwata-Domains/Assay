# Task: Playwright functional assertions in scripts

## Metadata
- **ID:** TASK-0069
- **Status:** pending
- **Phase:** Phase 25 — Functional + Integration Checks
- **Backlog:** P25-T04
- **Packet Path:** tasks/P25-T04-TASK-0069/
- **Dependencies:** TASK-0066, Phase 23 close
- **Primary Adapter:** code

## Objective
Extend Phase 23 multi-step scripts with assertion steps: `expect_text`, `expect_visible`, `expect_url`, `expect_not_text`. Add console error detection — a script fails if `console.error()` fires during execution. Step-level pass/fail is included in the result packet.

## Why This Task Exists
Phase 23 scripts capture screenshots but don't verify what's on screen. This task makes scripts genuine functional tests — a broken login flow or a missing element causes an explicit failure, not just a visual diff.

## Scope
- Add assertion step types to `runner_script.js`: `expect_text(selector, text)`, `expect_visible(selector)`, `expect_url(pattern)`, `expect_not_text(selector, text)`
- Console error listener: attach on page load; fail the step/script if `console.error` fires
- Each assertion step produces a `pass` or `fail` entry in the step results with actual vs expected
- Parser (`scripts/parser.py`) must accept and validate new assertion step types
- Tests: assertion pass/fail, console error detection, mixed step scripts

## Deliverable
Updated `runner_script.js` and `scripts/parser.py` with assertion step support; tests passing; step-level results in output packet.

## Constraints
- Assertion failures must not crash the runner — catch and record as step failure, continue remaining steps
- Console error detection applies per-step scope (errors after step N don't fail step N-1)
