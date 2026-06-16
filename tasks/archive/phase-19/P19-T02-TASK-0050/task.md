# Task: Smoke-test the Docker runner build and run end-to-end

## Metadata
- **ID:** TASK-0050
- **Status:** done
- **Phase:** P19-T02
- **Backlog:** P19-T02 — Smoke-test the Docker runner build and run end-to-end
- **Packet Path:** tasks/P19-T02-TASK-0050/
- **Dependencies:** P3 complete
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Build the Docker runner image from `runner/Dockerfile`, run it against a real URL, and verify it produces a valid `result.json` and a non-empty `screenshot.png`. Fix any issues found during the smoke test.

## Why This Task Exists
The Docker runner has never been built or run end-to-end. The image and run.js have been written but are untested. Before the CRM app can rely on this path, we need to confirm the build works and the runner produces usable output.

## Scope
- `docker build` the runner image
- `docker run` with ASSAY_TARGET_URL pointed at a reliable public URL (example.com)
- Verify `result.json` has `outcome: pass` and correct fields
- Verify `screenshot.png` is non-empty
- Fix any issues found (Dockerfile, run.js, package.json)

## Constraints
- Docker must be available in the build environment
- Internet access required for the target URL

## Escalation Conditions
- If Docker image pull fails (network/registry issue) — document and skip
