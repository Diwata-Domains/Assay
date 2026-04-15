"""Runner module unit tests — Docker calls are mocked."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from assay.runner.runner import DEFAULT_IMAGE, run


def _mock_result(returncode: int, stdout: str = "", stderr: str = "") -> MagicMock:
    m = MagicMock(spec=subprocess.CompletedProcess)
    m.returncode = returncode
    m.stdout = stdout
    m.stderr = stderr
    return m


def test_successful_run_returns_exit_0() -> None:
    with patch("assay.runner.runner.subprocess.run", return_value=_mock_result(0, stdout='{"outcome":"pass"}')):
        result = run("https://example.com", output_dir="/tmp/assay-test")
    assert result.exit_code == 0
    assert result.success is True
    assert result.output_dir == "/tmp/assay-test"


def test_failed_run_returns_exit_1() -> None:
    with patch("assay.runner.runner.subprocess.run", return_value=_mock_result(1, stderr="navigation failed")):
        result = run("https://example.com", output_dir="/tmp/assay-test")
    assert result.exit_code == 1
    assert result.success is False
    assert "navigation failed" in result.stderr


def test_correct_docker_flags_passed() -> None:
    with patch("assay.runner.runner.subprocess.run", return_value=_mock_result(0)) as mock_run:
        run("https://example.com", suite="smoke", output_dir="/tmp/out", image="custom-image:v1")
    cmd = mock_run.call_args[0][0]
    assert "docker" in cmd
    assert "custom-image:v1" in cmd
    assert "-e" in cmd
    assert "ASSAY_TARGET_URL=https://example.com" in cmd
    assert "ASSAY_SUITE=smoke" in cmd
    assert "ASSAY_OUTPUT_DIR=/output" in cmd
    assert "/tmp/out:/output" in cmd


def test_default_image_used_when_not_specified() -> None:
    with patch("assay.runner.runner.subprocess.run", return_value=_mock_result(0)) as mock_run:
        run("https://example.com", output_dir="/tmp/out")
    cmd = mock_run.call_args[0][0]
    assert DEFAULT_IMAGE in cmd


def test_output_dir_created_when_not_supplied() -> None:
    with patch("assay.runner.runner.subprocess.run", return_value=_mock_result(0)):
        with patch("assay.runner.runner.tempfile.mkdtemp", return_value="/tmp/assay-abc") as mock_mkdtemp:
            result = run("https://example.com")
    mock_mkdtemp.assert_called_once()
    assert result.output_dir == "/tmp/assay-abc"


def test_run_result_captures_stdout_stderr() -> None:
    with patch("assay.runner.runner.subprocess.run", return_value=_mock_result(0, stdout="ok", stderr="warn")):
        result = run("https://example.com", output_dir="/tmp/out")
    assert result.stdout == "ok"
    assert result.stderr == "warn"
