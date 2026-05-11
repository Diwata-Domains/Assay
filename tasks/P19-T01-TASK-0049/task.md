# Task: Replace html2canvas with html-to-image in the browser SDK

## Metadata
- **ID:** TASK-0049
- **Status:** done
- **Phase:** P19-T01
- **Backlog:** P19-T01 — Replace html2canvas with html-to-image in the browser SDK
- **Packet Path:** tasks/P19-T01-TASK-0049/
- **Dependencies:** P6 complete
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Replace `html2canvas` with `html-to-image` (toPng) in `packages/assay-sdk/src/screenshot.ts` and update `package.json` and tests accordingly.

## Why This Task Exists
html2canvas v1 has known limitations: poor CSS support, cross-origin resource failures, and rendering artifacts. html-to-image uses CSS serialization + SVG foreignObject and produces significantly better quality captures — needed for reliable CRM screenshot verification.

## Scope
- Remove `html2canvas` from `packages/assay-sdk/package.json`, add `html-to-image`
- Rewrite `packages/assay-sdk/src/screenshot.ts` to use `toPng`
- Update `packages/assay-sdk/tests/screenshot.test.ts` to mock `html-to-image`

## Constraints
- All existing tests must remain green
- No changes to the public API of `captureScreenshot()`

## Escalation Conditions
- None
