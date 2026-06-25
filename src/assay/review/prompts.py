# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Prompt assembly for the adversarial code-review reviewers.

Three roles, each a (system, user) prompt pair built over the gathered diff:

  - proposer: finds issues in the diff, reporting every candidate finding for coverage.
  - critic:   skeptically re-examines the proposer's findings, pruning false positives.
  - judge:    aggregates surviving findings into a single deterministic verdict + confidence.

The findings stage is told to maximize coverage (report everything, including low-confidence)
and to leave filtering to the critic/judge, per the Opus code-review guidance: moving the
confidence filter downstream raises recall without sacrificing precision.
"""

from __future__ import annotations

import json

_SEVERITY_VALUES = ("info", "warning", "error", "critical")

_FINDING_SHAPE = (
    'Each finding is an object: {"file": str, "line": int|null, '
    '"severity": "info"|"warning"|"error"|"critical", "message": str}. '
    "Line is 1-based, or null for a file-level finding."
)

PROPOSER_SYSTEM = (
    "You are a meticulous code reviewer. You are given a unified git diff. Find every issue "
    "you can: correctness bugs, security flaws, resource leaks, broken error handling, and "
    "logic errors introduced by the change. Report every issue you find, including ones you "
    "are uncertain about or consider low-severity — a separate verification step filters them. "
    "Your goal at this stage is coverage, not filtering.\n\n"
    'Respond with ONLY a JSON object: {"findings": [<finding>, ...]}. ' + _FINDING_SHAPE + " "
    "Do not include any prose outside the JSON."
)

CRITIC_SYSTEM = (
    "You are a skeptical senior reviewer auditing another reviewer's findings against a git "
    "diff. For each proposed finding, decide whether it is a real issue supported by the diff. "
    "Drop findings that are false positives, out of scope, pure style nits, or not actually "
    "introduced by this change. Keep the genuine ones, correcting severity if the proposer "
    "over- or under-rated it.\n\n"
    'Respond with ONLY a JSON object: {"findings": [<finding>, ...]} containing the findings '
    "you judge to be real. " + _FINDING_SHAPE + " Do not include any prose outside the JSON."
)

JUDGE_SYSTEM = (
    "You are the judge in an adversarial code review. You are given the diff, the proposer's "
    "findings, and the critic's surviving findings. Produce the final, deduplicated set of "
    "findings and an overall verdict.\n\n"
    'Respond with ONLY a JSON object: {"verdict": "pass"|"fail"|"inconclusive", '
    '"confidence": <float 0..1>, "summary": str, "findings": [<finding>, ...]}. '
    + _FINDING_SHAPE
    + " Use 'fail' when the change has issues that must be fixed, 'pass' when it is clean, and "
    "'inconclusive' when the diff is insufficient to judge. The runner re-derives the verdict "
    "deterministically from the findings, so be precise about severities. Do not include any "
    "prose outside the JSON."
)


def _diff_block(diff: str) -> str:
    return f"<diff>\n{diff}\n</diff>"


def proposer_prompt(diff: str) -> str:
    return "Review the following change.\n\n" + _diff_block(diff)


def critic_prompt(diff: str, proposer_findings: list[dict[str, object]]) -> str:
    return (
        "Audit these proposed findings against the change.\n\n"
        + _diff_block(diff)
        + "\n\n<proposed_findings>\n"
        + json.dumps({"findings": proposer_findings}, sort_keys=True)
        + "\n</proposed_findings>"
    )


def judge_prompt(
    diff: str,
    proposer_findings: list[dict[str, object]],
    critic_findings: list[dict[str, object]],
) -> str:
    return (
        "Aggregate the review into a final verdict.\n\n"
        + _diff_block(diff)
        + "\n\n<proposer_findings>\n"
        + json.dumps({"findings": proposer_findings}, sort_keys=True)
        + "\n</proposer_findings>\n\n<critic_findings>\n"
        + json.dumps({"findings": critic_findings}, sort_keys=True)
        + "\n</critic_findings>"
    )
