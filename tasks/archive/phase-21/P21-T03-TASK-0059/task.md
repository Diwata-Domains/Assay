# Task: Diff view in dashboard — before/after slider + highlighted regions

## Metadata
- **ID:** TASK-0059
- **Status:** done
- **Phase:** P21-T03
- **Backlog:** P21-T03 — Diff view in dashboard: before/after slider + highlighted regions
- **Packet Path:** tasks/P21-T03-TASK-0059/
- **Dependencies:** P21-T02 complete (pixel diff engine)
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Enhance the packet detail view to show an interactive before/after slider when a diff_result is present, alongside a diff-highlighted view tab. The slider reveals the baseline (before) vs candidate (after) screenshots via a draggable divider. A toggle switches to the red-highlighted diff image.

## Scope
- Packet detail (`GET /packet/{id}`): when `diff_result` is present and baseline exists
  - Load baseline screenshot as "before" image
  - Load candidate screenshot as "after" image
  - Render a draggable slider comparing both images
  - Render a tab/toggle to switch to the red-highlight diff image view
- All slider logic is pure inline CSS + JS (no external dependencies)
- Tests: `tests/test_diff_view.py` — packet with diff shows slider HTML; packet without diff does not; diff tab toggle HTML present

## Constraints
- No external JS libraries — vanilla JS only
- Gracefully degrade: if baseline image file doesn't exist on disk, fall back to the existing diff stats section without slider

## Escalation Conditions
- None
