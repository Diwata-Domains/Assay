# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Assay code-review verification mode.

Phase 30: adversarial / multi-agent AI code review as a verification MODE callable through the
grain verify bridge. This package holds the verdict contract (domain types + the
verdict -> packet outcome -> grain review mapping) and the packet formatter for code_review
results. The multi-agent runner that produces a CodeReviewResult is built on top of these
types (P30-T03+).
"""

from assay.review.client import (
    DEFAULT_MODEL,
    AnthropicLLMClient,
    LLMClient,
    LLMClientError,
)
from assay.review.diff import DiffGatherError, gather_diff
from assay.review.runner import ReviewerConfig, run_review
from assay.review.verdict import (
    CodeReviewFinding,
    CodeReviewResult,
    CodeReviewVerdict,
    GrainReviewVerdict,
    PacketOutcome,
    format_review_packet,
    grain_review_for_outcome,
    outcome_for_verdict,
)

__all__ = [
    "DEFAULT_MODEL",
    "AnthropicLLMClient",
    "CodeReviewFinding",
    "CodeReviewResult",
    "CodeReviewVerdict",
    "DiffGatherError",
    "GrainReviewVerdict",
    "LLMClient",
    "LLMClientError",
    "PacketOutcome",
    "ReviewerConfig",
    "format_review_packet",
    "gather_diff",
    "grain_review_for_outcome",
    "outcome_for_verdict",
    "run_review",
]
