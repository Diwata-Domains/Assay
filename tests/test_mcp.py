"""Tests: real engine-backed MCP server + X-Assay-Key auth on /mcp/*."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from assay.ingest.app import app as ingest_app
from assay.keys.store import create_key
from assay.runner.runner import RunResult
from assay.store import db as store


def _setup(tmp_path: Path) -> tuple[TestClient, str]:
    key_store = tmp_path / "keys.json"
    raw = create_key(str(key_store), label="agent")
    db = tmp_path / "store.db"
    ingest_app.state.key_store = str(key_store)
    ingest_app.state.output_dir = str(tmp_path / "out")
    ingest_app.state.store_db = str(db)
    store.init_db(db)
    return TestClient(ingest_app), raw


def _fake_runner(target: str, suite: str, output_dir: str, no_docker: bool) -> RunResult:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps({"outcome": "pass", "url": target, "suite": suite, "timestamp": "2026-06-25T10:00:00Z"})
    )
    Image.new("RGB", (8, 8), (10, 20, 30)).save(str(out / "screenshot.png"), "PNG")
    return RunResult(exit_code=0, output_dir=output_dir)


# --- auth ---


def test_tools_requires_api_key(tmp_path: Path) -> None:
    client, _ = _setup(tmp_path)
    resp = client.get("/mcp/tools")
    assert resp.status_code == 401


def test_tools_rejects_bad_key(tmp_path: Path) -> None:
    client, _ = _setup(tmp_path)
    resp = client.get("/mcp/tools", headers={"X-Assay-Key": "wrong"})
    assert resp.status_code == 401


def test_tools_lists_full_contract(tmp_path: Path) -> None:
    client, key = _setup(tmp_path)
    resp = client.get("/mcp/tools", headers={"X-Assay-Key": key})
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()["tools"]}
    assert {"run_verification", "get_report", "get_status", "list_runs", "approve_baseline"} <= names


def test_manifest_served(tmp_path: Path) -> None:
    client, key = _setup(tmp_path)
    resp = client.get("/mcp/manifest", headers={"X-Assay-Key": key})
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "assay"
    assert body["auth"]["header"] == "X-Assay-Key"
    assert any(e["path"] == "/ingest" for e in body["endpoints"])


def test_call_requires_api_key(tmp_path: Path) -> None:
    client, _ = _setup(tmp_path)
    resp = client.post("/mcp/call", json={"tool": "list_runs", "input": {}})
    assert resp.status_code == 401


# --- real engine dispatch ---


def test_run_verification_is_real_not_canned(tmp_path: Path) -> None:
    client, key = _setup(tmp_path)
    with patch("assay.api.service._default_runner", _fake_runner):
        resp = client.post(
            "/mcp/call",
            headers={"X-Assay-Key": key},
            json={"tool": "run_verification", "input": {"target": "https://example.com"}},
        )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["outcome"] == "pass"
    assert result["verification_id"]
    # The packet really exists in the store — not a canned "queued" job.
    assert store.list_packets(Path(ingest_app.state.store_db))


def test_run_verification_requires_target(tmp_path: Path) -> None:
    client, key = _setup(tmp_path)
    resp = client.post(
        "/mcp/call",
        headers={"X-Assay-Key": key},
        json={"tool": "run_verification", "input": {}},
    )
    assert resp.json()["error"] is not None


def test_get_report_and_status_after_run(tmp_path: Path) -> None:
    client, key = _setup(tmp_path)
    with patch("assay.api.service._default_runner", _fake_runner):
        run = client.post(
            "/mcp/call",
            headers={"X-Assay-Key": key},
            json={"tool": "run_verification", "input": {"target": "https://example.com"}},
        ).json()["result"]
    vid = run["verification_id"]

    report = client.post(
        "/mcp/call",
        headers={"X-Assay-Key": key},
        json={"tool": "get_report", "input": {"verification_id": vid}},
    ).json()["result"]
    assert report["outcome"] == "pass"

    status = client.post(
        "/mcp/call",
        headers={"X-Assay-Key": key},
        json={"tool": "get_status", "input": {"verification_id": vid}},
    ).json()["result"]
    assert status["status"] == "complete"


def test_get_status_pending_for_unknown(tmp_path: Path) -> None:
    client, key = _setup(tmp_path)
    status = client.post(
        "/mcp/call",
        headers={"X-Assay-Key": key},
        json={"tool": "get_status", "input": {"verification_id": "VERIFY-X-1"}},
    ).json()["result"]
    assert status["status"] == "pending"


def test_list_runs_and_baseline_loop(tmp_path: Path) -> None:
    client, key = _setup(tmp_path)
    with patch("assay.api.service._default_runner", _fake_runner):
        run = client.post(
            "/mcp/call",
            headers={"X-Assay-Key": key},
            json={"tool": "run_verification", "input": {"target": "https://example.com", "task_id": "TASK-0001"}},
        ).json()["result"]
    vid = run["verification_id"]

    runs = client.post(
        "/mcp/call",
        headers={"X-Assay-Key": key},
        json={"tool": "list_runs", "input": {"task_id": "TASK-0001"}},
    ).json()["result"]["runs"]
    assert len(runs) == 1

    approve = client.post(
        "/mcp/call",
        headers={"X-Assay-Key": key},
        json={"tool": "approve_baseline", "input": {"verification_id": vid}},
    ).json()["result"]
    assert approve["review_status"] == "approved"

    baselines = client.post(
        "/mcp/call",
        headers={"X-Assay-Key": key},
        json={"tool": "list_baselines", "input": {}},
    ).json()["result"]["baselines"]
    assert baselines == [{"url": "https://example.com", "verification_id": vid}]


def test_unknown_tool_returns_error(tmp_path: Path) -> None:
    client, key = _setup(tmp_path)
    resp = client.post(
        "/mcp/call",
        headers={"X-Assay-Key": key},
        json={"tool": "frobnicate", "input": {}},
    )
    assert "Unknown tool" in resp.json()["error"]


def test_approve_unknown_packet_returns_error(tmp_path: Path) -> None:
    client, key = _setup(tmp_path)
    resp = client.post(
        "/mcp/call",
        headers={"X-Assay-Key": key},
        json={"tool": "approve_baseline", "input": {"verification_id": "missing"}},
    )
    assert resp.json()["error"] is not None
