# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Multi-agent adversarial code-review runner.

Pipeline (deterministic given fixed model outputs):

  1. gather the diff (git refs or an explicit changed-file list).
  2. proposer reviewers find candidate issues (coverage-first).
  3. a critic/skeptic prunes false positives.
  4. a judge aggregates the surviving findings into a DETERMINISTIC verdict.

The verdict is NOT taken from the judge's free-text label. Instead it is re-derived from the
aggregated findings via `needs_fix_threshold` so that the same findings always map to the same
verdict regardless of model phrasing:

  - >= needs_fix_threshold error-or-critical findings  -> FAIL (needs_fix)
  - some findings, but below the threshold              -> PASS (approved)
  - no findings AND the judge could not reach a verdict -> INCONCLUSIVE (needs_human)

Transcripts (every reviewer's raw prompt + response) and the final findings are written under
the run output dir and referenced from `CodeReviewResult.transcript_refs`.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from assay.review.client import LLMClient
from assay.review.diff import gather_diff
from assay.review.prompts import (
    CRITIC_SYSTEM,
    JUDGE_SYSTEM,
    PROPOSER_SYSTEM,
    critic_prompt,
    judge_prompt,
    proposer_prompt,
)
from assay.review.verdict import (
    CodeReviewFinding,
    CodeReviewResult,
    CodeReviewVerdict,
)

_BLOCKING_SEVERITIES = ("error", "critical")
_SEVERITY_VALUES = ("info", "warning", "error", "critical")
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(frozen=True)
class ReviewerConfig:
    """Sizing for the adversarial reviewer pool."""

    agent_count: int = 2
    needs_fix_threshold: int = 1
    model: str = ""

    def __post_init__(self) -> None:
        if self.agent_count < 1:
            raise ValueError("agent_count must be >= 1")
        if self.needs_fix_threshold < 1:
            raise ValueError("needs_fix_threshold must be >= 1")


@dataclass
class _Transcript:
    role: str
    system: str
    prompt: str
    response: str

    def to_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "system": self.system,
            "prompt": self.prompt,
            "response": self.response,
        }


def _extract_json(text: str) -> dict[str, object]:
    """Parse the first JSON object out of a model response, tolerating surrounding prose."""
    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass
    match = _JSON_OBJECT_RE.search(stripped)
    if match:
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _coerce_finding(raw: object) -> Optional[CodeReviewFinding]:  # noqa: UP007
    if not isinstance(raw, dict):
        return None
    file = raw.get("file")
    message = raw.get("message")
    severity = raw.get("severity", "warning")
    if not isinstance(file, str) or not file:
        return None
    if not isinstance(message, str) or not message:
        return None
    if severity not in _SEVERITY_VALUES:
        severity = "warning"
    raw_line = raw.get("line")
    line = raw_line if isinstance(raw_line, int) and not isinstance(raw_line, bool) else None
    if line is not None and line < 0:
        line = None
    try:
        return CodeReviewFinding(file=file, severity=str(severity), message=message, line=line)
    except ValueError:
        return None


def _parse_findings(payload: dict[str, object]) -> list[CodeReviewFinding]:
    raw = payload.get("findings", [])
    if not isinstance(raw, list):
        return []
    out: list[CodeReviewFinding] = []
    for item in raw:
        finding = _coerce_finding(item)
        if finding is not None:
            out.append(finding)
    return out


def _dedupe(findings: list[CodeReviewFinding]) -> list[CodeReviewFinding]:
    seen: set[tuple[str, Optional[int], str, str]] = set()
    out: list[CodeReviewFinding] = []
    for f in findings:
        key = (f.file, f.line, f.severity, f.message)
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def _verdict_for_findings(
    findings: list[CodeReviewFinding],
    needs_fix_threshold: int,
    judge_verdict: Optional[str] = None,  # noqa: UP007  # the judge's raw label, if any
) -> CodeReviewVerdict:
    """Deterministic verdict mapping: same findings + threshold + judge label => same verdict.

    The blocking-findings rule is load-bearing and always wins (it is what makes the verdict
    reproducible from the findings rather than from model phrasing). Only when there are no
    blocking findings does the judge's explicit label break the tie between PASS and the
    INCONCLUSIVE / needs-human escape hatch.
    """
    blocking = sum(1 for f in findings if f.severity in _BLOCKING_SEVERITIES)
    if blocking >= needs_fix_threshold:
        return CodeReviewVerdict.FAIL
    if judge_verdict == CodeReviewVerdict.INCONCLUSIVE.value:
        return CodeReviewVerdict.INCONCLUSIVE
    if not findings and judge_verdict not in {v.value for v in CodeReviewVerdict}:
        return CodeReviewVerdict.INCONCLUSIVE
    return CodeReviewVerdict.PASS


def _write_artifacts(
    output_dir: Path,
    run_id: str,
    transcripts: list[_Transcript],
    findings: list[CodeReviewFinding],
) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    refs: list[str] = []

    transcript_path = output_dir / f"review-{run_id}-transcript.json"
    transcript_path.write_text(
        json.dumps([t.to_dict() for t in transcripts], indent=2, sort_keys=True)
    )
    refs.append(str(transcript_path))

    findings_path = output_dir / f"review-{run_id}-findings.json"
    findings_path.write_text(
        json.dumps([f.to_dict() for f in findings], indent=2, sort_keys=True)
    )
    refs.append(str(findings_path))
    return refs


def run_review(
    client: LLMClient,
    *,
    repo: str | Path = ".",
    base: Optional[str] = None,  # noqa: UP007
    head: Optional[str] = None,  # noqa: UP007
    changed_files: Optional[list[str]] = None,  # noqa: UP007
    diff: Optional[str] = None,  # noqa: UP007
    config: Optional[ReviewerConfig] = None,  # noqa: UP007
    output_dir: str | Path = "./assay-output/review",
    run_id: Optional[str] = None,  # noqa: UP007
) -> CodeReviewResult:
    """Run the adversarial review and return a deterministic CodeReviewResult.

    `client` is the injected LLMClient — never constructed here, so tests pass a fake and the
    real provider is opt-in. Provide either a pre-gathered `diff`, or `base`/`head` refs and/or
    a `changed_files` list to gather one from `repo`. Transcripts and findings are persisted
    under `output_dir` and referenced from the result.
    """
    cfg = config or ReviewerConfig()
    rid = run_id or uuid.uuid4().hex[:12]
    out = Path(output_dir)

    diff_text = diff if diff is not None else gather_diff(repo, base, head, changed_files)

    transcripts: list[_Transcript] = []
    reviewers: list[str] = []

    # --- proposers (one or more) ---
    proposed: list[CodeReviewFinding] = []
    p_prompt = proposer_prompt(diff_text)
    for i in range(cfg.agent_count):
        role = "proposer" if cfg.agent_count == 1 else f"proposer-{i + 1}"
        response = client.complete(PROPOSER_SYSTEM, p_prompt)
        transcripts.append(_Transcript(role, PROPOSER_SYSTEM, p_prompt, response))
        reviewers.append(role)
        proposed.extend(_parse_findings(_extract_json(response)))
    proposed = _dedupe(proposed)

    # --- critic / skeptic ---
    proposed_dicts = [f.to_dict() for f in proposed]
    c_prompt = critic_prompt(diff_text, proposed_dicts)
    critic_response = client.complete(CRITIC_SYSTEM, c_prompt)
    transcripts.append(_Transcript("critic", CRITIC_SYSTEM, c_prompt, critic_response))
    reviewers.append("critic")
    critic_findings = _dedupe(_parse_findings(_extract_json(critic_response)))

    # --- judge ---
    j_prompt = judge_prompt(diff_text, proposed_dicts, [f.to_dict() for f in critic_findings])
    judge_response = client.complete(JUDGE_SYSTEM, j_prompt)
    transcripts.append(_Transcript("judge", JUDGE_SYSTEM, j_prompt, judge_response))
    reviewers.append("judge")
    judge_payload = _extract_json(judge_response)

    final_findings = _dedupe(_parse_findings(judge_payload))
    raw_judge_verdict = judge_payload.get("verdict")
    judge_verdict = raw_judge_verdict if isinstance(raw_judge_verdict, str) else None

    verdict = _verdict_for_findings(final_findings, cfg.needs_fix_threshold, judge_verdict)

    raw_conf = judge_payload.get("confidence", 0.0)
    confidence = float(raw_conf) if isinstance(raw_conf, (int, float)) else 0.0
    confidence = max(0.0, min(1.0, confidence))

    summary = judge_payload.get("summary")
    if not isinstance(summary, str) or not summary:
        summary = _default_summary(verdict, final_findings)

    refs = _write_artifacts(out, rid, transcripts, final_findings)

    return CodeReviewResult(
        verdict=verdict,
        summary=summary,
        findings=final_findings,
        reviewers=reviewers,
        confidence=confidence,
        transcript_refs=refs,
    )


def _default_summary(verdict: CodeReviewVerdict, findings: list[CodeReviewFinding]) -> str:
    n = len(findings)
    noun = "finding" if n == 1 else "findings"
    return f"code review: {verdict.value} ({n} {noun})"
