"""Artifact collection unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from assay.runner.artifacts import ArtifactError, collect_artifacts
from assay.runner.runner import RunResult


def _make_result(exit_code: int = 0) -> RunResult:
    return RunResult(exit_code=exit_code, output_dir="/tmp/test")


def _write_result_json(directory: Path, data: dict) -> None:
    (directory / "result.json").write_text(json.dumps(data))


def _write_screenshot(directory: Path) -> None:
    (directory / "screenshot.png").write_bytes(b"\x89PNG\r\n")


_VALID_RESULT = {
    "outcome": "pass",
    "url": "https://example.com",
    "suite": "smoke",
    "timestamp": "2026-04-15T10:00:00Z",
    "error": None,
}


def test_full_bundle_from_valid_result_and_screenshot(tmp_path: Path) -> None:
    _write_result_json(tmp_path, _VALID_RESULT)
    _write_screenshot(tmp_path)
    bundle = collect_artifacts(str(tmp_path), _make_result())
    assert bundle.outcome == "pass"
    assert bundle.url == "https://example.com"
    assert bundle.suite == "smoke"
    assert bundle.screenshot_path is not None
    assert bundle.screenshot_path.endswith("screenshot.png")
    assert bundle.error is None


def test_missing_screenshot_gives_none(tmp_path: Path) -> None:
    _write_result_json(tmp_path, _VALID_RESULT)
    bundle = collect_artifacts(str(tmp_path), _make_result())
    assert bundle.screenshot_path is None


def test_missing_result_json_exit_0_gives_pass(tmp_path: Path) -> None:
    bundle = collect_artifacts(str(tmp_path), _make_result(exit_code=0))
    assert bundle.outcome == "pass"
    assert bundle.raw_result == {}


def test_missing_result_json_exit_1_gives_fail(tmp_path: Path) -> None:
    bundle = collect_artifacts(str(tmp_path), _make_result(exit_code=1))
    assert bundle.outcome == "fail"


def test_malformed_result_json_raises(tmp_path: Path) -> None:
    (tmp_path / "result.json").write_text("not valid json {{{")
    with pytest.raises(ArtifactError, match="failed to parse"):
        collect_artifacts(str(tmp_path), _make_result())


def test_error_field_populated_from_result_json(tmp_path: Path) -> None:
    data = {**_VALID_RESULT, "outcome": "fail", "error": "navigation timeout"}
    _write_result_json(tmp_path, data)
    bundle = collect_artifacts(str(tmp_path), _make_result(exit_code=1))
    assert bundle.error == "navigation timeout"


def test_missing_result_json_stderr_becomes_error(tmp_path: Path) -> None:
    result = RunResult(exit_code=1, output_dir=str(tmp_path), stderr="docker: image not found")
    bundle = collect_artifacts(str(tmp_path), result)
    assert bundle.error == "docker: image not found"
