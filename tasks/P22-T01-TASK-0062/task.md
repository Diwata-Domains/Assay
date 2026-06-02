# Task: Test script format — define steps in a JS/TS file

## Metadata
- **ID:** TASK-0062
- **Status:** pending
- **Phase:** Phase 22 — Multi-step Playwright Test Scripts
- **Backlog:** P22-T01
- **Packet Path:** tasks/P22-T01-TASK-0062/
- **Dependencies:** Phase 21 close
- **Primary Adapter:** code

## Objective
Define and implement the test script format — a JS or TypeScript file that describes a sequence of browser steps (navigate, click, fill, screenshot) for Assay to execute via the Docker runner. This is the format spec and parser task; execution is P22-T02.

## Why This Task Exists
Assay currently captures single-URL screenshots. Multi-step scripts unlock richer verification scenarios: login flows, form fills, multi-page journeys. The script format must be simple enough to write by hand and explicit enough for Assay to execute deterministically.

## Scope
- Define the script file format: a JS/TS module that exports a default array of step objects or an async function receiving a Playwright `page`
- Define supported step types: `navigate`, `click`, `fill`, `screenshot`, `wait`, `waitForSelector`
- Each step must produce a named screenshot when it includes a `screenshot` action; non-screenshot steps are transparent to the output packet
- Write a JSON schema or TypeScript type definition for the step contract
- Write the script parser/validator: reads a script file, validates step types and required fields, returns a normalized step list or a validation error list
- Add tests for valid and invalid script shapes

## Deliverable
Script format spec (in `docs/working/` or as a `SCRIPT_FORMAT.md`), step type definitions, and parser module in `src/assay/scripts/parser.py` (or equivalent). Tests passing.

## Constraints
- Scripts must be deterministic — no random behavior, no network side effects beyond Playwright navigation
- The format must be runnable from the CLI via `assay run --script <file>` without requiring a build step (load via Node.js `require`/`import` in the Docker runner)
- Errors in the script must produce a structured validation error, not a runtime crash
