"""E2E tests: assay run → runner → artifacts → formatter → writer → schema-valid packet.

Docker subprocess is mocked so tests run without a live Docker daemon.
The rest of the pipeline (artifact collection, formatting, writing, schema validation)
runs against real code with real temporary files.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import jsonschema
from typer.testing import CliRunner

from assay.cli.main import app
from assay.schemas import ASSAY_PAYLOAD

cli = CliRunner()

_RESULT_JSON = json.dumps(
    {
        "outcome": "pass",
        "url": "https://example.com",
        "suite": "default",
        "timestamp": "2026-04-18T10:00:00Z",
        "error": None,
    }
)


def _mock_subprocess(returncode: int = 0, result_json: str | None = _RESULT_JSON) -> MagicMock:
    """Return a mock subprocess.CompletedProcess that optionally writes result.json."""
    mock = MagicMock(spec=subprocess.CompletedProcess)
    mock.returncode = returncode
    mock.stdout = ""
    mock.stderr = ""
    mock._result_json = result_json
    return mock


def _write_output(output_dir: str, result_json: str | None) -> None:
    if result_json is not None:
        (Path(output_dir) / "result.json").write_text(result_json)


# ---------------------------------------------------------------------------
# E2E: pass path
# ---------------------------------------------------------------------------


def test_e2e_run_pass_writes_schema_valid_packet(tmp_path: Path) -> None:
    output_dir = str(tmp_path / "output")
    Path(output_dir).mkdir()

    def fake_subprocess_run(cmd, **kwargs):
        _write_output(output_dir, _RESULT_JSON)
        r = MagicMock(spec=subprocess.CompletedProcess)
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    with patch("subprocess.run", side_effect=fake_subprocess_run):
        result = cli.invoke(app, ["run", "--target", "https://example.com", "--output", output_dir])

    assert result.exit_code == 0, result.output
    assert "outcome: pass" in result.output
    assert "packet:" in result.output

    # locate written packet
    packets = list(Path(output_dir).glob("assay-*.json"))
    assert len(packets) == 1
    packet = json.loads(packets[0].read_text())
    jsonschema.validate(instance=packet, schema=ASSAY_PAYLOAD)


def test_e2e_run_pass_packet_fields(tmp_path: Path) -> None:
    output_dir = str(tmp_path / "output")
    Path(output_dir).mkdir()

    def fake_subprocess_run(cmd, **kwargs):
        _write_output(output_dir, _RESULT_JSON)
        r = MagicMock(spec=subprocess.CompletedProcess)
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    with patch("subprocess.run", side_effect=fake_subprocess_run):
        cli.invoke(app, ["run", "--target", "https://example.com", "--output", output_dir])

    packet = json.loads(list(Path(output_dir).glob("assay-*.json"))[0].read_text())
    assert packet["outcome"] == "pass"
    assert packet["severity"] == "info"
    assert packet["issue_type"] == "test_failure"
    assert "verification_id" in packet
    assert "verified_at" in packet


# ---------------------------------------------------------------------------
# E2E: fail path
# ---------------------------------------------------------------------------


def test_e2e_run_fail_exits_3_and_packet_valid(tmp_path: Path) -> None:
    output_dir = str(tmp_path / "output")
    Path(output_dir).mkdir()

    fail_json = json.dumps(
        {"outcome": "fail", "url": "https://example.com", "suite": "default",
         "timestamp": "2026-04-18T10:00:00Z", "error": "assertion failed"}
    )

    def fake_subprocess_run(cmd, **kwargs):
        _write_output(output_dir, fail_json)
        r = MagicMock(spec=subprocess.CompletedProcess)
        r.returncode = 1
        r.stdout = ""
        r.stderr = ""
        return r

    with patch("subprocess.run", side_effect=fake_subprocess_run):
        result = cli.invoke(app, ["run", "--target", "https://example.com", "--output", output_dir])

    assert result.exit_code == 3
    assert "outcome: fail" in result.output

    packet = json.loads(list(Path(output_dir).glob("assay-*.json"))[0].read_text())
    jsonschema.validate(instance=packet, schema=ASSAY_PAYLOAD)
    assert packet["outcome"] == "fail"
    assert packet["severity"] == "error"


# ---------------------------------------------------------------------------
# E2E: no result.json (container crash)
# ---------------------------------------------------------------------------


def test_e2e_run_no_result_json_falls_back_gracefully(tmp_path: Path) -> None:
    output_dir = str(tmp_path / "output")
    Path(output_dir).mkdir()

    def fake_subprocess_run(cmd, **kwargs):
        r = MagicMock(spec=subprocess.CompletedProcess)
        r.returncode = 1
        r.stdout = ""
        r.stderr = "container OOM"
        return r

    with patch("subprocess.run", side_effect=fake_subprocess_run):
        result = cli.invoke(app, ["run", "--target", "https://example.com", "--output", output_dir])

    assert result.exit_code in (1, 3)
    packets = list(Path(output_dir).glob("assay-*.json"))
    assert len(packets) == 1
    packet = json.loads(packets[0].read_text())
    jsonschema.validate(instance=packet, schema=ASSAY_PAYLOAD)


# ---------------------------------------------------------------------------
# E2E: suite flag flows through
# ---------------------------------------------------------------------------


def test_e2e_run_suite_passed_to_runner(tmp_path: Path) -> None:
    output_dir = str(tmp_path / "output")
    Path(output_dir).mkdir()
    captured_cmd: list[list[str]] = []

    def fake_subprocess_run(cmd, **kwargs):
        captured_cmd.append(list(cmd))
        _write_output(output_dir, _RESULT_JSON)
        r = MagicMock(spec=subprocess.CompletedProcess)
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    with patch("subprocess.run", side_effect=fake_subprocess_run):
        cli.invoke(app, ["run", "--target", "https://example.com", "--suite", "smoke", "--output", output_dir])

    assert any("smoke" in arg for arg in captured_cmd[0])
