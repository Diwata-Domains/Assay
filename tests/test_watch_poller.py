"""Unit tests for the file-change poller."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

from assay.watch.poller import debounce_and_wait, parse_watch_target, watch_once


def test_watch_once_returns_on_change(tmp_path: Path) -> None:
    f = tmp_path / "test.py"
    f.write_text("v1")

    def trigger_change() -> None:
        time.sleep(0.05)
        f.write_text("v2")

    import threading
    t = threading.Thread(target=trigger_change)
    t.start()
    watch_once(tmp_path, poll_interval_ms=20)
    t.join()


def test_watch_once_ignores_unchanged(tmp_path: Path) -> None:
    f = tmp_path / "test.py"
    f.write_text("stable")

    calls: list[int] = []
    original_sleep = time.sleep

    def counting_sleep(secs: float) -> None:
        calls.append(1)
        if len(calls) >= 3:
            f.write_text("changed")
        original_sleep(secs)

    with patch("assay.watch.poller.time.sleep", side_effect=counting_sleep):
        watch_once(tmp_path, poll_interval_ms=10)

    assert len(calls) >= 3


def test_watch_once_handles_missing_file_gracefully(tmp_path: Path) -> None:
    f = tmp_path / "existing.py"
    f.write_text("start")

    def remove_and_change() -> None:
        time.sleep(0.05)
        f.unlink()

    import threading
    t = threading.Thread(target=remove_and_change)
    t.start()
    watch_once(tmp_path, poll_interval_ms=20)
    t.join()


def test_debounce_waits_for_quiet_period(tmp_path: Path) -> None:
    f = tmp_path / "file.py"
    f.write_text("init")

    start = time.monotonic()
    debounce_and_wait(tmp_path, debounce_ms=100, poll_interval_ms=20)
    elapsed = time.monotonic() - start
    assert elapsed >= 0.09


def test_debounce_resets_on_subsequent_change(tmp_path: Path) -> None:
    f = tmp_path / "file.py"
    f.write_text("v1")

    change_times: list[float] = []

    original_snapshot = None

    def patched_snapshot(path: Path, glob: str | None = None) -> dict[str, float]:
        result = original_snapshot(path, glob)
        if len(change_times) == 0:
            change_times.append(time.monotonic())
            result["__fake__"] = float(len(change_times))
        return result

    from assay.watch import poller as _poller
    original_snapshot = _poller._snapshot  # type: ignore[attr-defined]

    with patch.object(_poller, "_snapshot", side_effect=patched_snapshot):
        start = time.monotonic()
        debounce_and_wait(tmp_path, debounce_ms=80, poll_interval_ms=20)
        elapsed = time.monotonic() - start

    assert elapsed >= 0.06


# ---------------------------------------------------------------------------
# parse_watch_target tests
# ---------------------------------------------------------------------------


def test_parse_plain_path_returns_no_glob() -> None:
    base, glob = parse_watch_target("src")
    assert base == Path("src")
    assert glob is None


def test_parse_dot_returns_no_glob() -> None:
    base, glob = parse_watch_target(".")
    assert glob is None


def test_parse_glob_star_star() -> None:
    base, glob = parse_watch_target("src/**/*.py")
    assert base == Path("src")
    assert glob == "**/*.py"


def test_parse_glob_single_star() -> None:
    base, glob = parse_watch_target("tests/*.ts")
    assert base == Path("tests")
    assert glob == "*.ts"


def test_parse_glob_no_base() -> None:
    base, glob = parse_watch_target("**/*.py")
    assert base == Path(".")
    assert glob == "**/*.py"


# ---------------------------------------------------------------------------
# glob-filtered snapshot / watch tests
# ---------------------------------------------------------------------------


def test_glob_filters_to_matching_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("py")
    (tmp_path / "app.js").write_text("js")

    triggered = []

    def trigger() -> None:
        time.sleep(0.05)
        (tmp_path / "app.py").write_text("changed")

    import threading
    t = threading.Thread(target=trigger)
    t.start()
    watch_once(tmp_path, glob="*.py", poll_interval_ms=20)
    triggered.append(True)
    t.join()
    assert triggered


def test_glob_ignores_non_matching_files(tmp_path: Path) -> None:
    py_file = tmp_path / "app.py"
    js_file = tmp_path / "app.js"
    py_file.write_text("stable")
    js_file.write_text("stable")

    calls: list[int] = []
    original_sleep = time.sleep

    def counting_sleep(secs: float) -> None:
        calls.append(1)
        if len(calls) == 3:
            js_file.write_text("changed js")
        if len(calls) >= 5:
            py_file.write_text("changed py")
        original_sleep(secs)

    with patch("assay.watch.poller.time.sleep", side_effect=counting_sleep):
        watch_once(tmp_path, glob="*.py", poll_interval_ms=10)

    assert len(calls) >= 5
