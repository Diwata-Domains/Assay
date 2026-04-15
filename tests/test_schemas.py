"""Validate each data contract schema against a known-good and a known-bad example."""

import jsonschema
import pytest

from assay.schemas import KEY_STORE, SCHEDULE_STATE, SDK_INGEST, SENTINEL_PAYLOAD


def _valid(schema: dict, instance: object) -> None:  # type: ignore[type-arg]
    jsonschema.validate(instance, schema)


def _invalid(schema: dict, instance: object) -> None:  # type: ignore[type-arg]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance, schema)


# ---------------------------------------------------------------------------
# Sentinel payload
# ---------------------------------------------------------------------------

SENTINEL_VALID = {
    "verification_id": "a1b2c3d4-0000-0000-0000-000000000001",
    "task_id": "TASK-0070",
    "issue_type": "test_failure",
    "severity": "error",
    "outcome": "fail",
    "summary": "Login button not found on /login page.",
    "artifact_refs": ["screenshots/login-failure.png"],
    "followup_candidates": [{"title": "Fix login selector", "description": "CSS selector changed in last deploy"}],
    "verified_at": "2026-04-15T10:00:00Z",
}

SENTINEL_VALID_STANDALONE = {
    "verification_id": "a1b2c3d4-0000-0000-0000-000000000002",
    "task_id": None,
    "issue_type": "screenshot_evidence",
    "severity": "info",
    "outcome": "pass",
    "summary": "Page rendered correctly.",
}


def test_sentinel_payload_valid() -> None:
    _valid(SENTINEL_PAYLOAD, SENTINEL_VALID)


def test_sentinel_payload_valid_standalone_null_task_id() -> None:
    _valid(SENTINEL_PAYLOAD, SENTINEL_VALID_STANDALONE)


def test_sentinel_payload_invalid_missing_required() -> None:
    _invalid(SENTINEL_PAYLOAD, {**SENTINEL_VALID, "outcome": None})  # outcome can't be null


def test_sentinel_payload_invalid_bad_issue_type() -> None:
    _invalid(SENTINEL_PAYLOAD, {**SENTINEL_VALID, "issue_type": "unknown_type"})


def test_sentinel_payload_invalid_bad_severity() -> None:
    _invalid(SENTINEL_PAYLOAD, {**SENTINEL_VALID, "severity": "low"})


# ---------------------------------------------------------------------------
# SDK ingest payload
# ---------------------------------------------------------------------------

SDK_VALID = {
    "captured_at": "2026-04-15T10:00:00Z",
    "url": "https://example.com/dashboard",
    "viewport": {"width": 1280, "height": 800},
    "user_agent": "Mozilla/5.0",
    "screenshot": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "user_comment": "Button is missing",
    "metadata": {"custom_key": "custom_value"},
}


def test_sdk_ingest_valid() -> None:
    _valid(SDK_INGEST, SDK_VALID)


def test_sdk_ingest_valid_null_comment() -> None:
    _valid(SDK_INGEST, {**SDK_VALID, "user_comment": None})


def test_sdk_ingest_invalid_missing_screenshot() -> None:
    payload = {k: v for k, v in SDK_VALID.items() if k != "screenshot"}
    _invalid(SDK_INGEST, payload)


def test_sdk_ingest_invalid_zero_viewport() -> None:
    _invalid(SDK_INGEST, {**SDK_VALID, "viewport": {"width": 0, "height": 800}})


# ---------------------------------------------------------------------------
# Key store
# ---------------------------------------------------------------------------

KEY_STORE_VALID = {
    "version": "1",
    "keys": [
        {
            "id": "key-uuid-0001",
            "label": "production",
            "hash": "$2b$12$examplehashvalue",
            "created_at": "2026-04-15T10:00:00Z",
            "revoked": False,
            "revoked_at": None,
        }
    ],
}


def test_key_store_valid() -> None:
    _valid(KEY_STORE, KEY_STORE_VALID)


def test_key_store_valid_empty_keys() -> None:
    _valid(KEY_STORE, {"version": "1", "keys": []})


def test_key_store_invalid_missing_version() -> None:
    _invalid(KEY_STORE, {"keys": []})


def test_key_store_invalid_missing_hash() -> None:
    bad_key = {k: v for k, v in KEY_STORE_VALID["keys"][0].items() if k != "hash"}
    _invalid(KEY_STORE, {"version": "1", "keys": [bad_key]})


# ---------------------------------------------------------------------------
# Schedule state
# ---------------------------------------------------------------------------

SCHEDULE_VALID = {
    "version": "1",
    "schedules": [
        {
            "id": "sched-uuid-0001",
            "cron": "0 2 * * *",
            "suite": "default",
            "target": "https://example.com",
            "created_at": "2026-04-15T10:00:00Z",
            "last_run": None,
            "last_result": None,
        }
    ],
}


def test_schedule_state_valid() -> None:
    _valid(SCHEDULE_STATE, SCHEDULE_VALID)


def test_schedule_state_valid_with_last_run() -> None:
    updated = {
        **SCHEDULE_VALID["schedules"][0],
        "last_run": "2026-04-15T02:00:00Z",
        "last_result": "success",
    }
    _valid(SCHEDULE_STATE, {"version": "1", "schedules": [updated]})


def test_schedule_state_invalid_bad_last_result() -> None:
    bad = {**SCHEDULE_VALID["schedules"][0], "last_result": "ok"}  # not in enum
    _invalid(SCHEDULE_STATE, {"version": "1", "schedules": [bad]})


def test_schedule_state_invalid_missing_cron() -> None:
    bad = {k: v for k, v in SCHEDULE_VALID["schedules"][0].items() if k != "cron"}
    _invalid(SCHEDULE_STATE, {"version": "1", "schedules": [bad]})
