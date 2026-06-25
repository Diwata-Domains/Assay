"""Tests for the multi-agent code-review runner (Phase 30, P30-T03).

A FakeLLMClient returns canned proposer/critic/judge outputs in call order, so the runner is
exercised end-to-end without ever touching a real model or network. Covers: findings parsed,
verdict deterministic for the approved AND needs_fix cases, git-diff input handled, and a clear,
actionable error when no client / optional dependency is configured.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from assay.review import (
    AnthropicLLMClient,
    CodeReviewFinding,
    CodeReviewResult,
    CodeReviewVerdict,
    DiffGatherError,
    GrainReviewVerdict,
    LLMClient,
    LLMClientError,
    PacketOutcome,
    ReviewerConfig,
    gather_diff,
    run_review,
)
from assay.review.client import DEFAULT_MODEL
from assay.review.diff import gather_diff as gather_diff_direct
from assay.review.runner import _extract_json, _verdict_for_findings


class FakeLLMClient:
    """Deterministic LLMClient: returns scripted responses in call order."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        if not self._responses:
            return "{}"
        return self._responses.pop(0)


def _err_finding(file: str = "src/x.py", line: int = 10) -> dict[str, object]:
    return {"file": file, "line": line, "severity": "error", "message": "null deref"}


def _findings_json(*findings: dict[str, object]) -> str:
    return json.dumps({"findings": list(findings)})


def _judge_json(verdict: str, *findings: dict[str, object], confidence: float = 0.9) -> str:
    return json.dumps(
        {
            "verdict": verdict,
            "confidence": confidence,
            "summary": f"judge says {verdict}",
            "findings": list(findings),
        }
    )


# --- fake protocol conformance ---


def test_fake_satisfies_llm_client_protocol() -> None:
    assert isinstance(FakeLLMClient(["{}"]), LLMClient)


# --- needs_fix (FAIL) case ---


def test_needs_fix_verdict_from_blocking_findings(tmp_path: Path) -> None:
    # agent_count=1 → proposer, critic, judge = 3 responses
    client = FakeLLMClient(
        [
            _findings_json(_err_finding()),
            _findings_json(_err_finding()),
            _judge_json("fail", _err_finding()),
        ]
    )
    result = run_review(
        client,
        diff="--- a/x\n+++ b/x\n@@\n+bug\n",
        config=ReviewerConfig(agent_count=1, needs_fix_threshold=1),
        output_dir=tmp_path,
        run_id="t1",
    )
    assert isinstance(result, CodeReviewResult)
    assert result.verdict is CodeReviewVerdict.FAIL
    assert result.outcome is PacketOutcome.FAIL
    assert result.grain_review is GrainReviewVerdict.NEEDS_FIX
    assert result.confidence == 0.9
    assert len(result.findings) == 1
    assert result.findings[0] == CodeReviewFinding(
        file="src/x.py", line=10, severity="error", message="null deref"
    )
    assert result.reviewers == ["proposer", "critic", "judge"]


def test_needs_fix_requires_threshold_count(tmp_path: Path) -> None:
    one_err = _judge_json("fail", _err_finding())
    client = FakeLLMClient([_findings_json(_err_finding()), _findings_json(), one_err])
    # threshold of 2 with a single blocking finding → not enough to fail → PASS
    result = run_review(
        client,
        diff="d",
        config=ReviewerConfig(agent_count=1, needs_fix_threshold=2),
        output_dir=tmp_path,
        run_id="t2",
    )
    assert result.verdict is CodeReviewVerdict.PASS
    assert result.grain_review is GrainReviewVerdict.APPROVED


# --- approved (PASS) case ---


def test_approved_verdict_when_no_blocking_findings(tmp_path: Path) -> None:
    client = FakeLLMClient(
        [_findings_json(), _findings_json(), _judge_json("pass", confidence=0.7)]
    )
    result = run_review(
        client,
        diff="clean diff",
        config=ReviewerConfig(agent_count=1),
        output_dir=tmp_path,
        run_id="t3",
    )
    assert result.verdict is CodeReviewVerdict.PASS
    assert result.outcome is PacketOutcome.PASS
    assert result.grain_review is GrainReviewVerdict.APPROVED
    assert result.findings == []
    assert result.confidence == 0.7


def test_info_finding_does_not_trigger_needs_fix(tmp_path: Path) -> None:
    info = {"file": "a.py", "line": 1, "severity": "info", "message": "style"}
    client = FakeLLMClient([_findings_json(info), _findings_json(info), _judge_json("pass", info)])
    result = run_review(
        client, diff="d", config=ReviewerConfig(agent_count=1), output_dir=tmp_path, run_id="t4"
    )
    assert result.verdict is CodeReviewVerdict.PASS
    assert len(result.findings) == 1  # finding still surfaced, just non-blocking


# --- inconclusive case ---


def test_inconclusive_when_no_findings_and_judge_unsure(tmp_path: Path) -> None:
    client = FakeLLMClient(
        [
            _findings_json(),
            _findings_json(),
            json.dumps({"verdict": "inconclusive", "confidence": 0.2, "summary": "n/a"}),
        ]
    )
    result = run_review(
        client, diff="", config=ReviewerConfig(agent_count=1), output_dir=tmp_path, run_id="t5"
    )
    assert result.verdict is CodeReviewVerdict.INCONCLUSIVE
    assert result.grain_review is GrainReviewVerdict.NEEDS_HUMAN


# --- determinism ---


def test_same_inputs_same_verdict(tmp_path: Path) -> None:
    def fresh() -> FakeLLMClient:
        return FakeLLMClient(
            [_findings_json(_err_finding()), _findings_json(_err_finding()), _judge_json("fail", _err_finding())]
        )

    r1 = run_review(fresh(), diff="d", config=ReviewerConfig(agent_count=1), output_dir=tmp_path, run_id="a")
    r2 = run_review(fresh(), diff="d", config=ReviewerConfig(agent_count=1), output_dir=tmp_path, run_id="b")
    assert r1.verdict is r2.verdict
    assert r1.findings == r2.findings


def test_verdict_ignores_judge_freetext_label(tmp_path: Path) -> None:
    # judge SAYS pass, but two blocking findings + threshold 1 deterministically forces FAIL
    client = FakeLLMClient(
        [
            _findings_json(_err_finding(line=1)),
            _findings_json(_err_finding(line=2)),
            _judge_json("pass", _err_finding(line=1), _err_finding(line=2)),
        ]
    )
    result = run_review(
        client, diff="d", config=ReviewerConfig(agent_count=1, needs_fix_threshold=1),
        output_dir=tmp_path, run_id="t6",
    )
    assert result.verdict is CodeReviewVerdict.FAIL


# --- multiple proposers ---


def test_multiple_proposers_called_and_deduped(tmp_path: Path) -> None:
    dup = _err_finding()
    client = FakeLLMClient(
        [_findings_json(dup), _findings_json(dup), _findings_json(dup), _judge_json("fail", dup)]
    )
    result = run_review(
        client, diff="d", config=ReviewerConfig(agent_count=2), output_dir=tmp_path, run_id="t7"
    )
    # 2 proposers + critic + judge = 4 calls
    assert len(client.calls) == 4
    assert result.reviewers == ["proposer-1", "proposer-2", "critic", "judge"]


# --- artifact persistence ---


def test_transcripts_and_findings_persisted(tmp_path: Path) -> None:
    client = FakeLLMClient(
        [_findings_json(_err_finding()), _findings_json(_err_finding()), _judge_json("fail", _err_finding())]
    )
    result = run_review(
        client, diff="d", config=ReviewerConfig(agent_count=1), output_dir=tmp_path, run_id="run9"
    )
    assert len(result.transcript_refs) == 2
    for ref in result.transcript_refs:
        assert Path(ref).exists()
    transcript = json.loads((tmp_path / "review-run9-transcript.json").read_text())
    roles = [t["role"] for t in transcript]
    assert roles == ["proposer", "critic", "judge"]
    findings = json.loads((tmp_path / "review-run9-findings.json").read_text())
    assert findings[0]["file"] == "src/x.py"


# --- malformed / prose-wrapped model output ---


def test_prose_wrapped_json_is_parsed(tmp_path: Path) -> None:
    wrapped = "Here are the findings:\n" + _findings_json(_err_finding()) + "\nThanks!"
    client = FakeLLMClient([wrapped, _findings_json(_err_finding()), _judge_json("fail", _err_finding())])
    result = run_review(
        client, diff="d", config=ReviewerConfig(agent_count=1), output_dir=tmp_path, run_id="t10"
    )
    assert result.verdict is CodeReviewVerdict.FAIL


def test_garbage_response_yields_no_findings(tmp_path: Path) -> None:
    client = FakeLLMClient(["not json at all", "still not json", "nope"])
    result = run_review(
        client, diff="d", config=ReviewerConfig(agent_count=1), output_dir=tmp_path, run_id="t11"
    )
    assert result.findings == []
    assert result.verdict is CodeReviewVerdict.INCONCLUSIVE  # no findings + judge unparseable


def test_bad_finding_fields_are_dropped(tmp_path: Path) -> None:
    bad = {"file": "", "severity": "error", "message": "m"}  # empty file → invalid
    good = _err_finding()
    client = FakeLLMClient(
        [_findings_json(bad, good), _findings_json(bad, good), _judge_json("fail", bad, good)]
    )
    result = run_review(
        client, diff="d", config=ReviewerConfig(agent_count=1), output_dir=tmp_path, run_id="t12"
    )
    assert len(result.findings) == 1
    assert result.findings[0].file == "src/x.py"


def test_unknown_severity_coerced_to_warning(tmp_path: Path) -> None:
    weird = {"file": "a.py", "line": 2, "severity": "fatal", "message": "boom"}
    client = FakeLLMClient([_findings_json(weird), _findings_json(weird), _judge_json("pass", weird)])
    result = run_review(
        client, diff="d", config=ReviewerConfig(agent_count=1), output_dir=tmp_path, run_id="t13"
    )
    assert result.findings[0].severity == "warning"
    assert result.verdict is CodeReviewVerdict.PASS  # warning is non-blocking


# --- git diff input ---


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
        "HOME": str(tmp_path),
    }

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True, env=env
        )

    git("init", "-q")
    (repo / "f.py").write_text("a = 1\n")
    git("add", "f.py")
    git("commit", "-q", "-m", "base")
    (repo / "f.py").write_text("a = 1\nb = 2\n")
    git("add", "f.py")
    git("commit", "-q", "-m", "head")
    return repo


def test_gather_diff_from_git_refs(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    diff = gather_diff(repo, base="HEAD~1", head="HEAD")
    assert "b = 2" in diff
    assert "f.py" in diff


def test_run_review_gathers_git_diff(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    client = FakeLLMClient([_findings_json(), _findings_json(), _judge_json("pass")])
    result = run_review(
        client,
        repo=repo,
        base="HEAD~1",
        head="HEAD",
        config=ReviewerConfig(agent_count=1),
        output_dir=tmp_path / "out",
        run_id="git1",
    )
    # the diff text reached the proposer's prompt
    proposer_system, proposer_prompt = client.calls[0]
    assert "b = 2" in proposer_prompt
    assert result.verdict is CodeReviewVerdict.PASS


def test_gather_diff_scoped_to_changed_files(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    diff = gather_diff_direct(repo, base="HEAD~1", head="HEAD", changed_files=["f.py"])
    assert "f.py" in diff
    # a path with no changes yields an empty diff
    empty = gather_diff_direct(repo, base="HEAD~1", head="HEAD", changed_files=["nope.py"])
    assert empty == ""


def test_gather_diff_missing_repo_raises() -> None:
    with pytest.raises(DiffGatherError, match="does not exist"):
        gather_diff("/no/such/repo/path", base="a", head="b")


def test_gather_diff_requires_both_refs(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    with pytest.raises(DiffGatherError, match="both base and head"):
        gather_diff(repo, base="HEAD", head=None)


def test_gather_diff_bad_ref_raises(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    with pytest.raises(DiffGatherError):
        gather_diff(repo, base="nonexistent-ref", head="HEAD")


# --- opt-in error when no client / dependency configured ---


def test_anthropic_client_missing_key_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    class _StubAnthropicModule:
        class Anthropic:  # noqa: D106
            def __init__(self, *a: object, **k: object) -> None:
                raise AssertionError("should not construct without a key")

    monkeypatch.setitem(__import__("sys").modules, "anthropic", _StubAnthropicModule)
    client = AnthropicLLMClient(api_key=None)
    with pytest.raises(LLMClientError, match="API key"):
        client.complete("sys", "prompt")


def test_anthropic_client_missing_dependency_raises_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "anthropic":
            raise ImportError("No module named 'anthropic'")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", fake_import)
    client = AnthropicLLMClient(api_key="sk-test")
    with pytest.raises(LLMClientError, match="anthropic"):
        client.complete("sys", "prompt")


def test_anthropic_client_default_model() -> None:
    assert AnthropicLLMClient().model == DEFAULT_MODEL == "claude-opus-4-8"


def test_anthropic_client_uses_injected_client() -> None:
    class FakeBlock:
        type = "text"
        text = '{"verdict": "pass"}'

    class FakeResponse:
        content = [FakeBlock()]

    class FakeMessages:
        def __init__(self) -> None:
            self.kwargs: dict[str, object] = {}

        def create(self, **kwargs: object) -> FakeResponse:
            self.kwargs = kwargs
            return FakeResponse()

    class FakeAnthropic:
        def __init__(self) -> None:
            self.messages = FakeMessages()

    fake = FakeAnthropic()
    client = AnthropicLLMClient(client=fake)
    out = client.complete("system text", "user text")
    assert out == '{"verdict": "pass"}'
    # determinism: no temperature/top_p/top_k sent (removed on Opus 4.8)
    assert "temperature" not in fake.messages.kwargs
    assert fake.messages.kwargs["model"] == "claude-opus-4-8"
    assert fake.messages.kwargs["system"] == "system text"


# --- config validation ---


def test_reviewer_config_rejects_bad_agent_count() -> None:
    with pytest.raises(ValueError, match="agent_count"):
        ReviewerConfig(agent_count=0)


def test_reviewer_config_rejects_bad_threshold() -> None:
    with pytest.raises(ValueError, match="needs_fix_threshold"):
        ReviewerConfig(needs_fix_threshold=0)


# --- internal helpers ---


def test_extract_json_handles_plain_object() -> None:
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_returns_empty_on_garbage() -> None:
    assert _extract_json("totally not json") == {}


def test_verdict_mapping_unit() -> None:
    err = CodeReviewFinding(file="a", severity="error", message="m")
    assert _verdict_for_findings([err], 1, "pass") is CodeReviewVerdict.FAIL  # blocking wins
    assert _verdict_for_findings([err], 2, "pass") is CodeReviewVerdict.PASS
    assert _verdict_for_findings([], 1, "pass") is CodeReviewVerdict.PASS
    assert _verdict_for_findings([], 1, None) is CodeReviewVerdict.INCONCLUSIVE
    assert _verdict_for_findings([], 1, "inconclusive") is CodeReviewVerdict.INCONCLUSIVE
