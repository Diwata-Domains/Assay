"""Tests for HTTP assertion engine (P25-T02)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from assay.checks.http import run_http_check
from assay.config import CheckConfig


def _mock_response(status: int = 200, body: str = "", elapsed_ms: int = 50) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.text = body
    return resp


def _check(**kwargs) -> CheckConfig:
    return CheckConfig(id="test", type="http", target="https://example.com", **kwargs)


# ---------------------------------------------------------------------------
# Status code assertion
# ---------------------------------------------------------------------------

def test_status_pass():
    with patch("httpx.get", return_value=_mock_response(200)):
        result = run_http_check(_check(expect_status=200))
    assert result.passed is True
    assert any(a.name == "status_code" and a.passed for a in result.assertions)


def test_status_fail():
    with patch("httpx.get", return_value=_mock_response(500)):
        result = run_http_check(_check(expect_status=200))
    assert result.passed is False
    a = next(x for x in result.assertions if x.name == "status_code")
    assert a.actual == "500"
    assert a.expected == "200"


# ---------------------------------------------------------------------------
# Response time assertion
# ---------------------------------------------------------------------------

def test_response_time_pass():
    with patch("httpx.get", return_value=_mock_response(200)):
        with patch("time.monotonic", side_effect=[0.0, 0.05]):
            result = run_http_check(_check(max_response_ms=200))
    assert result.passed is True
    a = next(x for x in result.assertions if x.name == "response_time_ms")
    assert a.passed is True


def test_response_time_fail():
    with patch("httpx.get", return_value=_mock_response(200)):
        with patch("time.monotonic", side_effect=[0.0, 1.5]):
            result = run_http_check(_check(max_response_ms=100))
    a = next(x for x in result.assertions if x.name == "response_time_ms")
    assert a.passed is False
    assert result.passed is False


# ---------------------------------------------------------------------------
# Body contains
# ---------------------------------------------------------------------------

def test_body_contains_pass():
    with patch("httpx.get", return_value=_mock_response(200, body='{"status":"ok"}')):
        result = run_http_check(_check(body_contains='"status"'))
    assert result.passed is True
    a = next(x for x in result.assertions if x.name == "body_contains")
    assert a.actual == "present"


def test_body_contains_fail():
    with patch("httpx.get", return_value=_mock_response(200, body="nothing here")):
        result = run_http_check(_check(body_contains="secret_key"))
    assert result.passed is False
    a = next(x for x in result.assertions if x.name == "body_contains")
    assert a.actual == "absent"


# ---------------------------------------------------------------------------
# JSON path
# ---------------------------------------------------------------------------

def test_json_path_pass():
    body = json.dumps({"data": {"status": "healthy"}})
    with patch("httpx.get", return_value=_mock_response(200, body=body)):
        result = run_http_check(_check(body_json_path="data.status", body_json_value="healthy"))
    assert result.passed is True
    a = next(x for x in result.assertions if "json_path" in x.name)
    assert a.passed is True


def test_json_path_fail_wrong_value():
    body = json.dumps({"data": {"status": "degraded"}})
    with patch("httpx.get", return_value=_mock_response(200, body=body)):
        result = run_http_check(_check(body_json_path="data.status", body_json_value="healthy"))
    assert result.passed is False
    a = next(x for x in result.assertions if "json_path" in x.name)
    assert a.actual == "degraded"


def test_json_path_fail_missing_key():
    body = json.dumps({"other": "value"})
    with patch("httpx.get", return_value=_mock_response(200, body=body)):
        result = run_http_check(_check(body_json_path="data.status", body_json_value="healthy"))
    assert result.passed is False
    a = next(x for x in result.assertions if "json_path" in x.name)
    assert "error" in a.actual


# ---------------------------------------------------------------------------
# Network error
# ---------------------------------------------------------------------------

def test_network_error_returns_failed_result():
    with patch("httpx.get", side_effect=Exception("connection refused")):
        result = run_http_check(_check(expect_status=200))
    assert result.passed is False
    assert result.error is not None
    assert "connection refused" in result.error
    assert result.assertions == []


# ---------------------------------------------------------------------------
# Multiple assertions
# ---------------------------------------------------------------------------

def test_multiple_assertions_all_pass():
    body = json.dumps({"ok": True})
    with patch("httpx.get", return_value=_mock_response(200, body=body)):
        result = run_http_check(_check(expect_status=200, body_contains='"ok"'))
    assert result.passed is True
    assert len(result.assertions) == 2


def test_multiple_assertions_one_fail():
    body = "plain text"
    with patch("httpx.get", return_value=_mock_response(200, body=body)):
        result = run_http_check(_check(expect_status=200, body_contains="missing"))
    assert result.passed is False
    assert any(a.passed for a in result.assertions)
    assert any(not a.passed for a in result.assertions)
