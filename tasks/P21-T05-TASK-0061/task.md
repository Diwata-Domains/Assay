# Task: assay run --compare — diff against baseline from CLI, exit 1 on regression

## Metadata
- **ID:** TASK-0061
- **Status:** done
- **Phase:** P21-T05
- **Backlog:** P21-T05 — assay run --compare: diff against baseline from CLI, exit 1 on regression
- **Packet Path:** tasks/P21-T05-TASK-0061/
- **Dependencies:** P21-T02 complete (diff engine), P16 complete (SQLite store)
- **Primary Adapter:** none
- **Secondary Adapters:** none

## Objective
Add `--compare` flag to `assay run`. When set, after capturing a screenshot, the CLI loads the baseline for the URL from the local store and runs the pixel diff. If diff_pct exceeds a configurable threshold (default 0.1%), the command exits with code 1 and prints a summary. If below threshold, exits 0.

## Scope
- `cli/main.py`: add `--compare` bool flag and `--threshold` float option (default 0.1) to `run` command
- After `assay run` captures the packet:
  - If `--compare` is set: check store for baseline via `get_baseline_for_url(url)`
  - If no baseline: print warning "no baseline set for <url>", exit 0
  - If baseline found: run `diff_images(baseline_png, candidate_png, diff_path)` 
  - Print diff summary: `diff: {pct}% changed ({changed}/{total} pixels)`
  - If `diff_pct > threshold`: print `REGRESSION detected (>{threshold}%)` and exit 1
  - If `diff_pct <= threshold`: print `clean — within threshold ({threshold}%)`
- Tests: `tests/test_compare_flag.py` — no baseline exits 0; below threshold exits 0; above threshold exits 1; output contains summary

## Constraints
- `--compare` only applies to screenshot runs (where the packet has a screenshot artifact)
- Uses the existing diff engine and store — no new storage
- Threshold is a percentage (0.0–100.0), defaults to 0.1

## Escalation Conditions
- None
