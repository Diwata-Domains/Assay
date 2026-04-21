"""Tests for Phase 11: screenshot persistence to disk + artifact_refs population."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from assay.cli.main import app as cli_app
from assay.ingest.app import app as ingest_app
from assay.keys.store import create_key

_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16  # minimal PNG header
_SCREENSHOT_B64 = base64.b64encode(_PNG_BYTES).decode()

_SDK_PAYLOAD = {
    "captured_at": "2026-04-21T10:00:00Z",
    "url": "https://example.com",
    "viewport": {"width": 1280, "height": 720},
    "user_agent": "Mozilla/5.0 (compatible; AssaySDK/1.0)",
    "screenshot": _SCREENSHOT_B64,
    "user_comment": None,
    "metadata": {},
}


@pytest.fixture()
def ingest_client(tmp_path: Path) -> tuple[TestClient, str, str]:
    store = str(tmp_path / "keys.json")
    output = str(tmp_path / "out")
    ingest_app.state.key_store = store
    ingest_app.state.output_dir = output
    return TestClient(ingest_app), store, output


# ---------------------------------------------------------------------------
# P11-T01: SDK screenshot saved to disk
# ---------------------------------------------------------------------------


def test_ingest_saves_screenshot_file(ingest_client: tuple[TestClient, str, str]) -> None:
    c, store, output = ingest_client
    key = create_key(store)
    r = c.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    assert r.status_code == 200
    pngs = list(Path(output).glob("*.png"))
    assert len(pngs) == 1


def test_ingest_screenshot_bytes_match(ingest_client: tuple[TestClient, str, str]) -> None:
    c, store, output = ingest_client
    key = create_key(store)
    c.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    png_path = next(Path(output).glob("*.png"))
    assert png_path.read_bytes() == _PNG_BYTES


def test_ingest_artifact_refs_populated(ingest_client: tuple[TestClient, str, str]) -> None:
    c, store, output = ingest_client
    key = create_key(store)
    c.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    packet = json.loads(next(Path(output).glob("assay-*.json")).read_text())
    refs = packet["artifact_refs"]
    assert isinstance(refs, list) and len(refs) == 1
    assert refs[0].endswith(".png")


def test_ingest_screenshot_named_by_verification_id(ingest_client: tuple[TestClient, str, str]) -> None:
    c, store, output = ingest_client
    key = create_key(store)
    c.post("/ingest", json=_SDK_PAYLOAD, headers={"X-Assay-Key": key})
    packet = json.loads(next(Path(output).glob("assay-*.json")).read_text())
    vid = str(packet["verification_id"])
    png_path = Path(output) / f"{vid}.png"
    assert png_path.exists()


# ---------------------------------------------------------------------------
# P11-T02: runner screenshot copied + referenced
# ---------------------------------------------------------------------------


def test_runner_screenshot_copied_to_output(tmp_path: Path) -> None:
    """screenshot.png written by runner ends up as {verification_id}.png in output dir."""
    runner_result = MagicMock()
    runner_result.exit_code = 0
    runner_result.stdout = ""
    runner_result.stderr = ""
    runner_result.output_dir = str(tmp_path)

    # Write fake screenshot and result.json into output dir (simulates Docker run)
    (tmp_path / "screenshot.png").write_bytes(_PNG_BYTES)
    (tmp_path / "result.json").write_text(
        json.dumps({
            "outcome": "pass",
            "url": "https://example.com",
            "suite": "default",
            "timestamp": "2026-04-21T10:00:00Z",
        })
    )

    runner = CliRunner()
    with patch("assay.runner.runner.run", return_value=runner_result):
        result = runner.invoke(
            cli_app,
            ["run", "--target", "https://example.com", "--output", str(tmp_path)],
        )
    assert result.exit_code == 0, result.output
    pngs = [p for p in tmp_path.glob("*.png") if p.name != "screenshot.png"]
    assert len(pngs) == 1, f"expected one verification-id PNG, got: {list(tmp_path.glob('*.png'))}"


def test_runner_artifact_refs_contains_png(tmp_path: Path) -> None:
    runner_result = MagicMock()
    runner_result.exit_code = 0
    runner_result.stdout = ""
    runner_result.stderr = ""
    runner_result.output_dir = str(tmp_path)

    (tmp_path / "screenshot.png").write_bytes(_PNG_BYTES)
    (tmp_path / "result.json").write_text(
        json.dumps({
            "outcome": "pass",
            "url": "https://example.com",
            "suite": "default",
            "timestamp": "2026-04-21T10:00:00Z",
        })
    )

    runner = CliRunner()
    with patch("assay.runner.runner.run", return_value=runner_result):
        runner.invoke(
            cli_app,
            ["run", "--target", "https://example.com", "--output", str(tmp_path)],
        )

    packet = json.loads(next(tmp_path.glob("assay-*.json")).read_text())
    refs = packet["artifact_refs"]
    assert any(r.endswith(".png") for r in refs)
