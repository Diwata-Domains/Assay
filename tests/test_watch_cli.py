"""CLI tests for assay run --watch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from assay.cli.main import app

runner = CliRunner()

_PASS_RESULT = MagicMock(output_dir="/tmp/out", exit_code=0, stdout="", stderr="")
_FAIL_RESULT = MagicMock(output_dir="/tmp/out", exit_code=1, stdout="", stderr="")


def _mock_bundle(outcome: str = "pass") -> MagicMock:
    b = MagicMock()
    b.outcome = outcome
    b.error = None
    b.screenshot_path = None
    return b


def _mock_packet() -> dict[str, object]:
    return {
        "verification_id": "aaaa-0000-4000-8000-000000000001",
        "task_id": None,
        "issue_type": "test_failure",
        "severity": "info",
        "outcome": "pass",
        "summary": "pass: https://example.com",
        "artifact_refs": [],
        "followup_candidates": [],
        "verified_at": "2026-04-29T10:00:00Z",
    }


@patch("assay.cli.main.write_packet", return_value=Path("/tmp/out/assay-test.json"))
@patch("assay.cli.main.format_packet", return_value=_mock_packet())
@patch("assay.cli.main._artifacts.collect_artifacts", return_value=_mock_bundle("pass"))
@patch("assay.cli.main._runner.run", return_value=_PASS_RESULT)
def test_watch_flag_runs_initial_then_stops_on_ctrl_c(mock_run, mock_collect, mock_fmt, mock_write, tmp_path):  # type: ignore[no-untyped-def]
    call_count = 0

    def fake_watch_once(path: Path, poll_interval_ms: int = 200) -> None:
        nonlocal call_count
        call_count += 1
        if call_count >= 1:
            raise KeyboardInterrupt

    with patch("assay.watch.poller.watch_once", side_effect=fake_watch_once):
        with patch("assay.watch.poller.debounce_and_wait"):
            result = runner.invoke(
                app, ["run", "--target", "https://example.com", "--watch", "--watch-path", str(tmp_path)]
            )

    assert result.exit_code == 0
    assert "watch stopped" in result.output
    mock_run.assert_called_once()


@patch("assay.cli.main.write_packet", return_value=Path("/tmp/out/assay-test.json"))
@patch("assay.cli.main.format_packet", return_value=_mock_packet())
@patch("assay.cli.main._artifacts.collect_artifacts", return_value=_mock_bundle("pass"))
@patch("assay.cli.main._runner.run", return_value=_PASS_RESULT)
def test_watch_reruns_on_change(mock_run, mock_collect, mock_fmt, mock_write, tmp_path):  # type: ignore[no-untyped-def]
    call_count = 0

    def fake_watch_once(path: Path, poll_interval_ms: int = 200) -> None:
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise KeyboardInterrupt

    with patch("assay.watch.poller.watch_once", side_effect=fake_watch_once):
        with patch("assay.watch.poller.debounce_and_wait"):
            result = runner.invoke(
                app, ["run", "--target", "https://example.com", "--watch", "--watch-path", str(tmp_path)]
            )

    assert result.exit_code == 0
    assert mock_run.call_count == 2
    assert "change detected" in result.output


@patch("assay.cli.main.write_packet", return_value=Path("/tmp/out/assay-test.json"))
@patch("assay.cli.main.format_packet", return_value=_mock_packet())
@patch("assay.cli.main._artifacts.collect_artifacts", return_value=_mock_bundle("pass"))
@patch("assay.cli.main._runner.run", return_value=_PASS_RESULT)
def test_no_watch_flag_exits_normally(mock_run, mock_collect, mock_fmt, mock_write, tmp_path):  # type: ignore[no-untyped-def]
    result = runner.invoke(app, ["run", "--target", "https://example.com"])
    assert result.exit_code == 0
    mock_run.assert_called_once()


@patch("assay.cli.main.write_packet", return_value=Path("/tmp/out/assay-test.json"))
@patch("assay.cli.main.format_packet", return_value=_mock_packet())
@patch("assay.cli.main._artifacts.collect_artifacts", return_value=_mock_bundle("pass"))
@patch("assay.cli.main._runner.run", return_value=_PASS_RESULT)
def test_watch_prints_watching_path(mock_run, mock_collect, mock_fmt, mock_write, tmp_path):  # type: ignore[no-untyped-def]
    with patch("assay.watch.poller.watch_once", side_effect=KeyboardInterrupt):
        with patch("assay.watch.poller.debounce_and_wait"):
            result = runner.invoke(
                app, ["run", "--target", "https://example.com", "--watch", "--watch-path", str(tmp_path)]
            )
    assert "watching:" in result.output
