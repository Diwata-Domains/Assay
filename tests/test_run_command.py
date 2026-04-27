"""Tests for the assay run command wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from assay.cli.main import app
from assay.runner.artifacts import ArtifactBundle, ArtifactError
from assay.runner.runner import RunResult

runner = CliRunner(env={"NO_COLOR": "1"})

_PASS_BUNDLE = ArtifactBundle(
    outcome="pass",
    url="https://example.com",
    suite="default",
    timestamp="2026-04-15T10:00:00Z",
    error=None,
    screenshot_path=None,
    raw_result={},
)

_FAIL_BUNDLE = ArtifactBundle(
    outcome="fail",
    url="https://example.com",
    suite="default",
    timestamp="2026-04-15T10:00:00Z",
    error="assertion failed",
    screenshot_path=None,
    raw_result={},
)

_INCONCLUSIVE_BUNDLE = ArtifactBundle(
    outcome="inconclusive",
    url="https://example.com",
    suite="default",
    timestamp="",
    error=None,
    screenshot_path=None,
    raw_result={},
)

_MOCK_RUN_RESULT = RunResult(exit_code=0, output_dir="/tmp/assay-test")
_MOCK_PACKET: dict[str, object] = {"verification_id": "test-id", "outcome": "pass"}
_MOCK_PACKET_PATH = Path("/tmp/assay-test/assay-20260416-test-id.json")


def _base_patches(bundle: ArtifactBundle):  # type: ignore[no-untyped-def]
    """Stack of patches needed for all run command tests."""
    return (
        patch("assay.runner.runner.run", return_value=_MOCK_RUN_RESULT),
        patch("assay.runner.artifacts.collect_artifacts", return_value=bundle),
        patch("assay.cli.main.format_packet", return_value=_MOCK_PACKET),
        patch("assay.cli.main.write_packet", return_value=_MOCK_PACKET_PATH),
    )


def test_run_missing_target_exits_2() -> None:
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 2


def test_run_pass_exits_0() -> None:
    with (
        patch("assay.runner.runner.run", return_value=_MOCK_RUN_RESULT),
        patch("assay.runner.artifacts.collect_artifacts", return_value=_PASS_BUNDLE),
        patch("assay.cli.main.format_packet", return_value=_MOCK_PACKET),
        patch("assay.cli.main.write_packet", return_value=_MOCK_PACKET_PATH),
    ):
        result = runner.invoke(app, ["run", "--target", "https://example.com"])
    assert result.exit_code == 0
    assert "outcome: pass" in result.output


def test_run_fail_exits_3() -> None:
    with (
        patch("assay.runner.runner.run", return_value=_MOCK_RUN_RESULT),
        patch("assay.runner.artifacts.collect_artifacts", return_value=_FAIL_BUNDLE),
        patch("assay.cli.main.format_packet", return_value=_MOCK_PACKET),
        patch("assay.cli.main.write_packet", return_value=_MOCK_PACKET_PATH),
    ):
        result = runner.invoke(app, ["run", "--target", "https://example.com"])
    assert result.exit_code == 3
    assert "outcome: fail" in result.output


def test_run_inconclusive_exits_1() -> None:
    with (
        patch("assay.runner.runner.run", return_value=_MOCK_RUN_RESULT),
        patch("assay.runner.artifacts.collect_artifacts", return_value=_INCONCLUSIVE_BUNDLE),
        patch("assay.cli.main.format_packet", return_value=_MOCK_PACKET),
        patch("assay.cli.main.write_packet", return_value=_MOCK_PACKET_PATH),
    ):
        result = runner.invoke(app, ["run", "--target", "https://example.com"])
    assert result.exit_code == 1
    assert "outcome: inconclusive" in result.output


def test_run_artifact_error_exits_1() -> None:
    with (
        patch("assay.runner.runner.run", return_value=_MOCK_RUN_RESULT),
        patch(
            "assay.runner.artifacts.collect_artifacts",
            side_effect=ArtifactError("failed to parse result.json"),
        ),
    ):
        result = runner.invoke(app, ["run", "--target", "https://example.com"])
    assert result.exit_code == 1


def test_run_passes_suite_to_runner() -> None:
    run_mock = MagicMock(return_value=_MOCK_RUN_RESULT)
    with (
        patch("assay.runner.runner.run", run_mock),
        patch("assay.runner.artifacts.collect_artifacts", return_value=_PASS_BUNDLE),
        patch("assay.cli.main.format_packet", return_value=_MOCK_PACKET),
        patch("assay.cli.main.write_packet", return_value=_MOCK_PACKET_PATH),
    ):
        runner.invoke(app, ["run", "--target", "https://example.com", "--suite", "smoke"])
    run_mock.assert_called_once()
    _args, kwargs = run_mock.call_args
    assert kwargs.get("suite") == "smoke" or _args[1] == "smoke"


def test_run_prints_packet_path() -> None:
    with (
        patch("assay.runner.runner.run", return_value=_MOCK_RUN_RESULT),
        patch("assay.runner.artifacts.collect_artifacts", return_value=_PASS_BUNDLE),
        patch("assay.cli.main.format_packet", return_value=_MOCK_PACKET),
        patch("assay.cli.main.write_packet", return_value=_MOCK_PACKET_PATH),
    ):
        result = runner.invoke(app, ["run", "--target", "https://example.com"])
    assert "packet:" in result.output


def test_run_writer_error_exits_1() -> None:
    with (
        patch("assay.runner.runner.run", return_value=_MOCK_RUN_RESULT),
        patch("assay.runner.artifacts.collect_artifacts", return_value=_PASS_BUNDLE),
        patch("assay.formatter.formatter.format_packet", return_value=_MOCK_PACKET),
        patch("assay.cli.main.write_packet", side_effect=OSError("disk full")),
    ):
        result = runner.invoke(app, ["run", "--target", "https://example.com"])
    assert result.exit_code == 1
