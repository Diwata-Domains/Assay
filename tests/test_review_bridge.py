"""Integration tests for the code-review bridge (Phase 30, STAGE 3).

Covers the full bridge-callable mode end-to-end without a model or network:

  - a FIXTURE git repo with a base/head diff,
  - a FAKE LLM client returning scripted proposer/critic/judge JSON,
  - `assay review` produces a SCHEMA-VALID packet,
  - verdict -> outcome mapping (needs_fix -> 'fail', approved -> 'pass'),
  - verification_id passthrough (the grain-issued VERIFY-XXXX-NNN survives),
  - `--submit` reuses _do_submit() to copy the packet to the Grain output path,
  - the MCP `code_review` tool returns the verdict over /mcp/call.

Both the approved and needs_fix cases are exercised on each surface.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import jsonschema  # type: ignore[import-untyped]
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from assay.cli.main import app
from assay.ingest.app import app as ingest_app
from assay.keys.store import create_key
from assay.schemas import ASSAY_PAYLOAD
from assay.store import db as store

runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})


# --------------------------------------------------------------------------- #
# fakes + fixtures
# --------------------------------------------------------------------------- #


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


def _err_finding() -> dict[str, object]:
    return {"file": "app.py", "line": 3, "severity": "error", "message": "null deref"}


def _judge_json(verdict: str, *findings: dict[str, object]) -> str:
    return json.dumps(
        {
            "verdict": verdict,
            "confidence": 0.9,
            "summary": f"judge says {verdict}",
            "findings": list(findings),
        }
    )


def _needs_fix_client() -> FakeLLMClient:
    # agent_count=2 -> proposer-1, proposer-2, critic, judge = 4 responses.
    # One blocking (error) finding survives to the judge -> FAIL / needs_fix.
    f = _err_finding()
    return FakeLLMClient(
        [
            json.dumps({"findings": [f]}),
            json.dumps({"findings": [f]}),
            json.dumps({"findings": [f]}),
            _judge_json("fail", f),
        ]
    )


def _approved_client() -> FakeLLMClient:
    # agent_count=2: no findings, judge says pass -> PASS / approved.
    return FakeLLMClient(
        [
            json.dumps({"findings": []}),
            json.dumps({"findings": []}),
            json.dumps({"findings": []}),
            _judge_json("pass"),
        ]
    )


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture()
def fixture_repo(tmp_path: Path) -> tuple[Path, str, str]:
    """A real git repo with a base commit and a head commit that introduces a diff."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t.test")
    _git(repo, "config", "user.name", "t")
    (repo / "app.py").write_text("def f():\n    return 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    (repo / "app.py").write_text("def f():\n    x = None\n    return x.value\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "head")
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    return repo, base, head


def _write_config(tmp_path: Path, grain_output: Path | None = None) -> Path:
    cfg = tmp_path / "assay.toml"
    body = (
        f'[output]\ndirectory = "{tmp_path}/out"\n'
        f'[store]\ndb = "{tmp_path}/store.db"\n'
        f'[keys]\nstore = "{tmp_path}/keys.json"\n'
        f'[schedule]\nstore = "{tmp_path}/sched.json"\n'
        '[review]\nagent_count = 2\nneeds_fix_threshold = 1\n'
    )
    if grain_output is not None:
        body += f'[grain]\noutput_path = "{grain_output}"\n'
    cfg.write_text(body)
    return cfg


# --------------------------------------------------------------------------- #
# CLI: `assay review`
# --------------------------------------------------------------------------- #


def test_review_needs_fix_emits_schema_valid_fail_packet(
    tmp_path: Path, fixture_repo: tuple[Path, str, str]
) -> None:
    repo, base, head = fixture_repo
    cfg = _write_config(tmp_path)
    fake = _needs_fix_client()

    with patch("assay.api.service._default_review_client", return_value=fake):
        result = runner.invoke(
            app,
            [
                "--config", str(cfg),
                "review",
                "--repo", str(repo),
                "--base", base,
                "--head", head,
                "--task-id", "TASK-0099",
                "--verification-id", "VERIFY-0099-001",
                "--format", "json",
            ],
        )

    # needs_fix verdict -> outcome 'fail' -> CLI exit code 3
    assert result.exit_code == 3, result.output
    payload = json.loads(result.output.strip().splitlines()[-1])
    assert payload["verdict"] == "fail"
    assert payload["outcome"] == "fail"
    assert payload["grain_review"] == "needs_fix"
    assert payload["verification_id"] == "VERIFY-0099-001"

    packet = json.loads(Path(str(payload["packet_path"])).read_text())
    jsonschema.validate(instance=packet, schema=ASSAY_PAYLOAD)
    assert packet["outcome"] == "fail"
    assert packet["verification_id"] == "VERIFY-0099-001"
    assert packet["task_id"] == "TASK-0099"
    # the runner persisted transcript + findings artifacts and they are referenced
    assert packet["artifact_refs"]


def test_review_approved_emits_schema_valid_pass_packet(
    tmp_path: Path, fixture_repo: tuple[Path, str, str]
) -> None:
    repo, base, head = fixture_repo
    cfg = _write_config(tmp_path)
    fake = _approved_client()

    with patch("assay.api.service._default_review_client", return_value=fake):
        result = runner.invoke(
            app,
            [
                "--config", str(cfg),
                "review",
                "--repo", str(repo),
                "--base", base,
                "--head", head,
                "--task-id", "TASK-0100",
                "--verification-id", "VERIFY-0100-001",
                "--format", "json",
            ],
        )

    # approved verdict -> outcome 'pass' -> CLI exit code 0
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip().splitlines()[-1])
    assert payload["verdict"] == "pass"
    assert payload["outcome"] == "pass"
    assert payload["grain_review"] == "approved"
    assert payload["verification_id"] == "VERIFY-0100-001"

    packet = json.loads(Path(str(payload["packet_path"])).read_text())
    jsonschema.validate(instance=packet, schema=ASSAY_PAYLOAD)
    assert packet["outcome"] == "pass"
    assert packet["verification_id"] == "VERIFY-0100-001"


def test_review_persists_packet_to_store(
    tmp_path: Path, fixture_repo: tuple[Path, str, str]
) -> None:
    repo, base, head = fixture_repo
    cfg = _write_config(tmp_path)
    fake = _needs_fix_client()

    with patch("assay.api.service._default_review_client", return_value=fake):
        runner.invoke(
            app,
            [
                "--config", str(cfg),
                "review",
                "--repo", str(repo),
                "--base", base,
                "--head", head,
                "--verification-id", "VERIFY-0101-001",
            ],
        )

    packets = store.list_packets(tmp_path / "store.db")
    vids = {str(p.get("verification_id")) for p in packets}
    assert "VERIFY-0101-001" in vids


def test_review_submit_reuses_do_submit_copy(
    tmp_path: Path, fixture_repo: tuple[Path, str, str]
) -> None:
    repo, base, head = fixture_repo
    grain_inbox = tmp_path / "grain-inbox"
    cfg = _write_config(tmp_path, grain_output=grain_inbox)
    fake = _approved_client()

    with patch("assay.api.service._default_review_client", return_value=fake):
        result = runner.invoke(
            app,
            [
                "--config", str(cfg),
                "review",
                "--repo", str(repo),
                "--base", base,
                "--head", head,
                "--verification-id", "VERIFY-0102-001",
                "--submit",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "submitted:" in result.output
    # _do_submit copied the schema-valid packet into the Grain output path
    copied = list(grain_inbox.glob("assay-*.json"))
    assert len(copied) == 1
    submitted = json.loads(copied[0].read_text())
    jsonschema.validate(instance=submitted, schema=ASSAY_PAYLOAD)
    assert submitted["verification_id"] == "VERIFY-0102-001"
    assert submitted["outcome"] == "pass"


# --------------------------------------------------------------------------- #
# MCP: code_review over /mcp/call
# --------------------------------------------------------------------------- #


def _mcp_setup(tmp_path: Path) -> tuple[TestClient, str]:
    key_store = tmp_path / "keys.json"
    raw = create_key(str(key_store), label="agent")
    db = tmp_path / "store.db"
    ingest_app.state.key_store = str(key_store)
    ingest_app.state.output_dir = str(tmp_path / "out")
    ingest_app.state.store_db = str(db)
    store.init_db(db)
    return TestClient(ingest_app), raw


def test_mcp_code_review_in_tool_contract(tmp_path: Path) -> None:
    client, key = _mcp_setup(tmp_path)
    resp = client.get("/mcp/tools", headers={"X-Assay-Key": key})
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()["tools"]}
    assert "code_review" in names


def test_mcp_code_review_requires_auth(tmp_path: Path) -> None:
    client, _ = _mcp_setup(tmp_path)
    resp = client.post(
        "/mcp/call",
        json={"tool": "code_review", "input": {"diff": "d"}},
    )
    assert resp.status_code == 401


def test_mcp_code_review_returns_needs_fix_verdict(
    tmp_path: Path, fixture_repo: tuple[Path, str, str]
) -> None:
    repo, base, head = fixture_repo
    client, key = _mcp_setup(tmp_path)
    fake = _needs_fix_client()

    with patch("assay.api.service._default_review_client", return_value=fake):
        resp = client.post(
            "/mcp/call",
            headers={"X-Assay-Key": key},
            json={
                "tool": "code_review",
                "input": {
                    "repo": str(repo),
                    "base": base,
                    "head": head,
                    "task_id": "TASK-0103",
                    "verification_id": "VERIFY-0103-001",
                },
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    result = body["result"]
    assert result["verdict"] == "fail"
    assert result["outcome"] == "fail"
    assert result["verification_id"] == "VERIFY-0103-001"
    assert result["status"] == "complete"

    # the packet was really persisted and is schema-valid
    packets = store.list_packets(tmp_path / "store.db")
    packet = next(p for p in packets if p.get("verification_id") == "VERIFY-0103-001")
    jsonschema.validate(instance=packet, schema=ASSAY_PAYLOAD)
    assert packet["outcome"] == "fail"


def test_mcp_code_review_returns_approved_verdict(
    tmp_path: Path, fixture_repo: tuple[Path, str, str]
) -> None:
    repo, base, head = fixture_repo
    client, key = _mcp_setup(tmp_path)
    fake = _approved_client()

    with patch("assay.api.service._default_review_client", return_value=fake):
        resp = client.post(
            "/mcp/call",
            headers={"X-Assay-Key": key},
            json={
                "tool": "code_review",
                "input": {
                    "repo": str(repo),
                    "base": base,
                    "head": head,
                    "verification_id": "VERIFY-0104-001",
                },
            },
        )

    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["verdict"] == "pass"
    assert result["outcome"] == "pass"
    assert result["verification_id"] == "VERIFY-0104-001"
    assert result["status"] == "complete"


def test_mcp_code_review_requires_diff_or_refs(tmp_path: Path) -> None:
    client, key = _mcp_setup(tmp_path)
    resp = client.post(
        "/mcp/call",
        headers={"X-Assay-Key": key},
        json={"tool": "code_review", "input": {"repo": "."}},
    )
    assert resp.status_code == 200
    assert resp.json()["error"] is not None
