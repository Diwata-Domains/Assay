"""Tests for the direct (no-Docker) runner mode."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from assay.runner.runner import _find_runner_script, run_direct, run_script_direct


def test_find_runner_script_exists():
    path = _find_runner_script()
    assert path.exists()
    assert path.name == "runner_script.js"


def test_find_runner_script_is_valid_js():
    path = _find_runner_script()
    content = path.read_text(encoding="utf-8")
    assert "playwright" in content
    assert "ASSAY_TARGET_URL" in content
    assert "ASSAY_SCRIPT_FILE" in content


def _mock_run(exit_code: int, stdout: str = "", stderr: str = ""):
    mock = MagicMock()
    mock.returncode = exit_code
    mock.stdout = stdout
    mock.stderr = stderr
    return mock


def test_run_direct_pass(tmp_path):
    result_data = {
        "outcome": "pass", "url": "https://example.com",
        "suite": "default", "timestamp": "2026-06-12T00:00:00Z", "error": None,
    }
    (tmp_path / "result.json").write_text(json.dumps(result_data))
    (tmp_path / "screenshot.png").write_bytes(b"PNG")

    with patch("subprocess.run", return_value=_mock_run(0, stdout=json.dumps(result_data))) as mock_sub:
        result = run_direct("https://example.com", output_dir=str(tmp_path))

    assert result.exit_code == 0
    assert result.success is True
    mock_sub.assert_called_once()
    cmd = mock_sub.call_args[0][0]
    assert cmd[0] == "node"
    assert "runner_script.js" in cmd[1]


def test_run_direct_fail(tmp_path):
    with patch("subprocess.run", return_value=_mock_run(1, stderr="page crashed")):
        result = run_direct("https://example.com", output_dir=str(tmp_path))

    assert result.exit_code == 1
    assert result.success is False
    assert result.stderr == "page crashed"


def test_run_direct_sets_env_vars(tmp_path):
    with patch("subprocess.run", return_value=_mock_run(0)) as mock_sub:
        run_direct("https://example.com", suite="smoke", output_dir=str(tmp_path))

    env = mock_sub.call_args[1]["env"]
    assert env["ASSAY_TARGET_URL"] == "https://example.com"
    assert env["ASSAY_SUITE"] == "smoke"
    assert env["ASSAY_OUTPUT_DIR"] == str(tmp_path)


def test_run_direct_sets_node_path(tmp_path):
    with patch("subprocess.run", return_value=_mock_run(0)) as mock_sub:
        run_direct("https://example.com", output_dir=str(tmp_path))

    env = mock_sub.call_args[1]["env"]
    assert "NODE_PATH" in env
    assert "node_modules" in env["NODE_PATH"]


def test_run_direct_creates_output_dir_if_none():
    with patch("subprocess.run", return_value=_mock_run(0)):
        with patch("tempfile.mkdtemp", return_value="/tmp/assay-test") as mock_tmp:
            run_direct("https://example.com")

    mock_tmp.assert_called_once()


def test_run_script_direct_sets_script_env(tmp_path):
    script = tmp_path / "flow.json"
    script.write_text('{"name":"t","steps":[]}')

    with patch("subprocess.run", return_value=_mock_run(0)) as mock_sub:
        run_script_direct(script, output_dir=str(tmp_path))

    env = mock_sub.call_args[1]["env"]
    assert env["ASSAY_SCRIPT_FILE"] == str(script.resolve())
    assert "ASSAY_TARGET_URL" not in env


def test_run_script_direct_does_not_use_docker(tmp_path):
    script = tmp_path / "flow.json"
    script.write_text('{"name":"t","steps":[]}')

    with patch("subprocess.run", return_value=_mock_run(0)) as mock_sub:
        run_script_direct(script, output_dir=str(tmp_path))

    cmd = mock_sub.call_args[0][0]
    assert "docker" not in " ".join(cmd)
    assert cmd[0] == "node"
