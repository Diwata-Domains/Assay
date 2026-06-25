# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Tests for the Assay telemetry emitter (Pulse Phase 3 / P3-T02).

Covers the opt-in gate (off by default → no events / no queue file), the queue
fallback when enabled without a reachable endpoint, the endpoint POST path, the
exact verification.completed envelope+payload, the strict never-raises contract,
and that run_verification returns identically with telemetry on.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from assay import telemetry
from assay.api import service
from assay.runner.runner import RunResult
from assay.telemetry import (
    ENDPOINT_ENV_VAR,
    EVENT_VERIFICATION_COMPLETED,
    TELEMETRY_EVENT_VERSION,
    TelemetryEvent,
    emit,
    flush,
    is_enabled,
    make_verification_completed_event,
)


def _write_png(path: Path, color: tuple[int, int, int]) -> None:
    Image.new("RGB", (10, 10), color).save(str(path), "PNG")


def _fake_runner_factory(outcome: str, color: tuple[int, int, int] = (10, 20, 30)):  # type: ignore[no-untyped-def]
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


def _queue_path(root: Path) -> Path:
    return root / ".assay" / "telemetry_queue.jsonl"


def _read_queue(root: Path) -> list[dict]:
    path = _queue_path(root)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _toml(tmp_path: Path, *, enabled: bool = False, endpoint: str = "") -> None:
    body = "[telemetry]\n" f"enabled = {'true' if enabled else 'false'}\n"
    if endpoint:
        body += f'endpoint = "{endpoint}"\n'
    (tmp_path / "assay.toml").write_text(body)


# ── Gate: off by default ───────────────────────────────────────────────────────

def test_disabled_by_default_emits_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    # No assay.toml at all → disabled.
    assert is_enabled() is False
    emit(make_verification_completed_event("V-1", "https://x", passed=True, checks_total=1, checks_passed=1))
    flush()
    assert not _queue_path(tmp_path).exists()


def test_toml_disabled_emits_nothing(tmp_path, monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    _toml(tmp_path, enabled=False)
    assert is_enabled() is False
    emit(make_verification_completed_event("V-1", "https://x", passed=True, checks_total=1, checks_passed=1))
    flush()
    assert not _queue_path(tmp_path).exists()


# ── Gate: enabled paths + exact envelope ───────────────────────────────────────

def test_toml_enabled_no_endpoint_queues_exact_envelope(tmp_path, monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    _toml(tmp_path, enabled=True)
    assert is_enabled() is True

    emit(
        make_verification_completed_event(
            "VERIFY-0001-001", "https://example.com", passed=False, checks_total=3, checks_passed=2
        )
    )
    flush()  # delivery is async (daemon thread); drain it for a deterministic read

    queued = _read_queue(tmp_path)
    assert len(queued) == 1
    event = queued[0]
    # Exact envelope shape (matches Grain / Pulse).
    assert set(event) == {"event_type", "version", "timestamp", "payload"}
    assert event["event_type"] == EVENT_VERIFICATION_COMPLETED
    assert event["version"] == TELEMETRY_EVENT_VERSION
    assert event["timestamp"]
    assert event["payload"] == {
        "run_id": "VERIFY-0001-001",
        "target": "https://example.com",
        "passed": False,
        "checks_total": 3,
        "checks_passed": 2,
    }


def test_env_endpoint_enables_and_falls_back_to_queue(tmp_path, monkeypatch):
    monkeypatch.setenv(ENDPOINT_ENV_VAR, "http://127.0.0.1:9/none")
    monkeypatch.chdir(tmp_path)
    # No toml block, but env var alone turns telemetry on.
    assert is_enabled() is True

    emit(make_verification_completed_event("V-9", "https://x", passed=True, checks_total=1, checks_passed=1))
    flush()

    queued = _read_queue(tmp_path)
    assert len(queued) == 1
    assert queued[0]["event_type"] == EVENT_VERIFICATION_COMPLETED
    assert queued[0]["payload"]["run_id"] == "V-9"


def test_endpoint_post_success_does_not_queue(tmp_path, monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    _toml(tmp_path, enabled=True, endpoint="https://pulse.example/ingest")

    posted: list[tuple[str, dict]] = []

    def _fake_post(endpoint, record):
        posted.append((endpoint, record))
        return True

    monkeypatch.setattr(telemetry, "_try_post", _fake_post)

    emit(make_verification_completed_event("V-2", "https://x", passed=True, checks_total=2, checks_passed=2))
    flush()

    assert len(posted) == 1
    assert posted[0][0] == "https://pulse.example/ingest"
    assert posted[0][1]["event_type"] == EVENT_VERIFICATION_COMPLETED
    assert posted[0][1]["payload"]["checks_passed"] == 2
    assert not _queue_path(tmp_path).exists()


def test_env_endpoint_wins_over_toml_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv(ENDPOINT_ENV_VAR, "https://env.example/ingest")
    monkeypatch.chdir(tmp_path)
    _toml(tmp_path, enabled=True, endpoint="https://toml.example/ingest")

    seen: list[str] = []

    def _fake_post(endpoint, record):
        seen.append(endpoint)
        return True

    monkeypatch.setattr(telemetry, "_try_post", _fake_post)
    emit(make_verification_completed_event("V-3", "https://x", passed=True, checks_total=1, checks_passed=1))
    flush()

    assert seen == ["https://env.example/ingest"]


# ── Never raises ───────────────────────────────────────────────────────────────

def test_emit_never_raises_on_unwritable_queue(tmp_path, monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    _toml(tmp_path, enabled=True)

    def _boom(record):
        raise OSError("disk full")

    monkeypatch.setattr(telemetry, "_append_to_queue", _boom)
    # Must not raise — neither on the caller's thread nor the dispatch thread.
    emit(make_verification_completed_event("V-4", "https://x", passed=True, checks_total=1, checks_passed=1))
    flush()


def test_emit_never_raises_when_disabled_and_toml_broken(tmp_path, monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "assay.toml").write_text("this = [ not valid toml\n")
    # Broken toml → is_enabled falls back to False, emit is a no-op.
    assert is_enabled() is False
    emit(make_verification_completed_event("V-5", "https://x", passed=True, checks_total=1, checks_passed=1))
    flush()
    assert not _queue_path(tmp_path).exists()


# ── Event builder is typed + versioned ─────────────────────────────────────────

def test_event_builder_is_versioned():
    event = make_verification_completed_event("V-6", "https://x", passed=True, checks_total=4, checks_passed=4)
    assert isinstance(event, TelemetryEvent)
    assert event.version == TELEMETRY_EVENT_VERSION
    assert event.event_type == EVENT_VERIFICATION_COMPLETED
    assert event.timestamp


# ── Integration with run_verification ──────────────────────────────────────────

def test_run_verification_off_by_default_no_emit(tmp_path, monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    result = service.run_verification(
        "https://example.com",
        output_dir=str(tmp_path / "out"),
        store_db=str(tmp_path / "store.db"),
        runner_fn=_fake_runner_factory("pass"),
    )
    flush()
    assert result["outcome"] == "pass"
    assert not _queue_path(tmp_path).exists()


def test_run_verification_emits_when_enabled(tmp_path, monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    _toml(tmp_path, enabled=True)  # no endpoint → queue fallback

    result = service.run_verification(
        "https://example.com",
        output_dir=str(tmp_path / "out"),
        store_db=str(tmp_path / "store.db"),
        verification_id="VERIFY-0042-001",
        runner_fn=_fake_runner_factory("fail"),
    )
    flush()

    queued = _read_queue(tmp_path)
    assert len(queued) == 1
    event = queued[0]
    assert event["event_type"] == EVENT_VERIFICATION_COMPLETED
    assert event["payload"] == {
        "run_id": "VERIFY-0042-001",
        "target": "https://example.com",
        "passed": False,
        "checks_total": 1,
        "checks_passed": 0,
    }
    # The verification result is unaffected by telemetry being on.
    assert result["verification_id"] == "VERIFY-0042-001"
    assert result["outcome"] == "fail"


def test_run_verification_identical_result_with_telemetry_on(tmp_path, monkeypatch):
    monkeypatch.delenv(ENDPOINT_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)

    # Baseline: telemetry off.
    off = service.run_verification(
        "https://example.com",
        output_dir=str(tmp_path / "out_off"),
        store_db=str(tmp_path / "off.db"),
        verification_id="VERIFY-0001-001",
        runner_fn=_fake_runner_factory("pass"),
    )

    # Now with telemetry on (queue fallback).
    _toml(tmp_path, enabled=True)
    on = service.run_verification(
        "https://example.com",
        output_dir=str(tmp_path / "out_on"),
        store_db=str(tmp_path / "on.db"),
        verification_id="VERIFY-0001-001",
        runner_fn=_fake_runner_factory("pass"),
    )
    flush()

    # The result dict is identical except for path-bearing fields.
    ignore = {"packet_path", "artifact_refs"}
    assert {k: v for k, v in on.items() if k not in ignore} == {
        k: v for k, v in off.items() if k not in ignore
    }
    # And telemetry did fire on the second run.
    assert len(_read_queue(tmp_path)) == 1


def test_run_verification_unreachable_endpoint_queues_and_result_unaffected(tmp_path, monkeypatch):
    # An unreachable endpoint (real urllib failure) returns False from _try_post,
    # so the event falls back to the on-disk queue and the result is unaffected.
    monkeypatch.setenv(ENDPOINT_ENV_VAR, "http://127.0.0.1:9/none")
    monkeypatch.chdir(tmp_path)

    result = service.run_verification(
        "https://example.com",
        output_dir=str(tmp_path / "out"),
        store_db=str(tmp_path / "store.db"),
        runner_fn=_fake_runner_factory("pass"),
    )
    flush()
    assert result["outcome"] == "pass"
    # Unreachable endpoint → fell back to queue.
    assert len(_read_queue(tmp_path)) == 1


def test_run_verification_never_raises_when_post_explodes(tmp_path, monkeypatch):
    # Even if _try_post itself raised (it shouldn't in production — it guards its
    # own errors), the background _deliver swallows it: emission is strictly
    # side-band and the verification result is unaffected.
    monkeypatch.setenv(ENDPOINT_ENV_VAR, "https://pulse.example/ingest")
    monkeypatch.chdir(tmp_path)

    def _boom_post(endpoint, record):
        raise RuntimeError("network on fire")

    monkeypatch.setattr(telemetry, "_try_post", _boom_post)

    result = service.run_verification(
        "https://example.com",
        output_dir=str(tmp_path / "out"),
        store_db=str(tmp_path / "store.db"),
        runner_fn=_fake_runner_factory("pass"),
    )
    flush()
    assert result["outcome"] == "pass"
