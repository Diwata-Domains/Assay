"""Tests: engine service layer (assay.api.service) — full loop, no Docker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from assay.api import service
from assay.runner.runner import RunResult
from assay.store import db as store


def _write_png(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (10, 10), color).save(str(path), "PNG")


def _fake_runner_factory(outcome: str, color: tuple[int, int, int] = (10, 20, 30)):  # type: ignore[no-untyped-def]
    """Return a runner_fn that writes a real result.json + screenshot — no Docker."""

    def _runner(target: str, suite: str, output_dir: str, no_docker: bool) -> RunResult:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "result.json").write_text(
            json.dumps(
                {
                    "outcome": outcome,
                    "url": target,
                    "suite": suite,
                    "timestamp": "2026-06-25T10:00:00Z",
                }
            )
        )
        _write_png(out / "screenshot.png", color)
        return RunResult(exit_code=0 if outcome == "pass" else 1, output_dir=output_dir)

    return _runner


def test_run_verification_persists_real_packet(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    out = tmp_path / "out"
    result = service.run_verification(
        "https://example.com",
        output_dir=str(out),
        store_db=str(db),
        task_id="TASK-0099",
        runner_fn=_fake_runner_factory("pass"),
    )
    assert result["outcome"] == "pass"
    assert result["task_id"] == "TASK-0099"
    assert Path(str(result["packet_path"])).exists()

    # The packet is in the real store, not canned
    packets = store.list_packets(db)
    assert len(packets) == 1
    assert packets[0]["verification_id"] == result["verification_id"]


def test_run_verification_uses_provided_verification_id(tmp_path: Path) -> None:
    result = service.run_verification(
        "https://example.com",
        output_dir=str(tmp_path / "out"),
        store_db=str(tmp_path / "store.db"),
        verification_id="VERIFY-0099-001",
        runner_fn=_fake_runner_factory("pass"),
    )
    assert result["verification_id"] == "VERIFY-0099-001"


def test_run_verification_requires_target(tmp_path: Path) -> None:
    with pytest.raises(service.ServiceError, match="target is required"):
        service.run_verification(
            "",
            output_dir=str(tmp_path),
            store_db=str(tmp_path / "store.db"),
            runner_fn=_fake_runner_factory("pass"),
        )


def test_get_report_reads_real_store(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    run = service.run_verification(
        "https://example.com",
        output_dir=str(tmp_path / "out"),
        store_db=str(db),
        runner_fn=_fake_runner_factory("fail"),
    )
    report = service.get_report(str(run["verification_id"]), store_db=str(db))
    assert report is not None
    assert report["outcome"] == "fail"
    assert report["url"] == "https://example.com"


def test_get_report_returns_none_for_unknown(tmp_path: Path) -> None:
    store.init_db(tmp_path / "store.db")
    assert service.get_report("nope", store_db=str(tmp_path / "store.db")) is None


def test_run_then_diff_detects_regression(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    out = tmp_path / "out"
    # First run becomes the baseline (red).
    base = service.run_verification(
        "https://example.com",
        output_dir=str(out),
        store_db=str(db),
        runner_fn=_fake_runner_factory("pass", color=(255, 0, 0)),
    )
    service.approve_baseline(str(base["verification_id"]), store_db=str(db))

    # Second run is a different colour → regression above threshold.
    second = service.run_verification(
        "https://example.com",
        output_dir=str(out),
        store_db=str(db),
        threshold=0.1,
        runner_fn=_fake_runner_factory("pass", color=(0, 255, 0)),
    )
    assert second["regression"] is True
    assert "diff" in second


def test_list_runs_filters_by_task(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    out = tmp_path / "out"
    service.run_verification(
        "https://a.example.com",
        output_dir=str(out),
        store_db=str(db),
        task_id="TASK-0001",
        runner_fn=_fake_runner_factory("pass"),
    )
    service.run_verification(
        "https://b.example.com",
        output_dir=str(out),
        store_db=str(db),
        task_id="TASK-0002",
        runner_fn=_fake_runner_factory("pass"),
    )
    runs = service.list_runs(store_db=str(db), task_id="TASK-0001")
    assert len(runs) == 1
    assert runs[0]["task_id"] == "TASK-0001"


def test_approve_and_list_baselines(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    run = service.run_verification(
        "https://example.com",
        output_dir=str(tmp_path / "out"),
        store_db=str(db),
        runner_fn=_fake_runner_factory("pass"),
    )
    res = service.approve_baseline(str(run["verification_id"]), store_db=str(db))
    assert res["review_status"] == "approved"
    assert res["url"] == "https://example.com"
    baselines = service.list_baselines(store_db=str(db))
    assert baselines == [{"url": "https://example.com", "verification_id": run["verification_id"]}]


def test_reject_baseline_marks_rejected(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    run = service.run_verification(
        "https://example.com",
        output_dir=str(tmp_path / "out"),
        store_db=str(db),
        runner_fn=_fake_runner_factory("pass"),
    )
    res = service.reject_baseline(str(run["verification_id"]), store_db=str(db))
    assert res["review_status"] == "rejected"
    report = service.get_report(str(run["verification_id"]), store_db=str(db))
    assert report is not None
    assert report["review_status"] == "rejected"


def test_set_baseline_unknown_packet_raises(tmp_path: Path) -> None:
    store.init_db(tmp_path / "store.db")
    with pytest.raises(service.ServiceError, match="not found"):
        service.set_baseline("missing", store_db=str(tmp_path / "store.db"))
