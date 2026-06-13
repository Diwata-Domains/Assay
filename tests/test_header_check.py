"""Tests for header + auth check types (P25-T03)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from assay.checks.auth import _resolve_key, run_auth_check
from assay.checks.header import run_header_check
from assay.config import CheckConfig


def _check(type: str = "header", **kwargs: object) -> CheckConfig:
    return CheckConfig(id="test", type=type, target="https://example.com", **kwargs)  # type: ignore[arg-type]


def _mock_response(status: int = 200, headers: dict[str, str] | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    from httpx import Headers
    resp.headers = Headers(headers or {})
    return resp


# ---------------------------------------------------------------------------
# Header check — expect_header (presence)
# ---------------------------------------------------------------------------

def test_header_present_pass():
    with patch("httpx.get", return_value=_mock_response(200, {"Content-Type": "application/json"})):
        result = run_header_check(_check(expect_header="Content-Type"))
    assert result.passed is True
    a = next(x for x in result.assertions if "header_present" in x.name)
    assert a.actual == "present"


def test_header_present_fail():
    with patch("httpx.get", return_value=_mock_response(200, {})):
        result = run_header_check(_check(expect_header="X-Custom-Header"))
    assert result.passed is False
    a = next(x for x in result.assertions if "header_present" in x.name)
    assert a.actual == "absent"


def test_header_check_case_insensitive():
    with patch("httpx.get", return_value=_mock_response(200, {"content-type": "text/html"})):
        result = run_header_check(_check(expect_header="Content-Type"))
    assert result.passed is True


# ---------------------------------------------------------------------------
# Header check — expect_value
# ---------------------------------------------------------------------------

def test_header_value_pass():
    with patch("httpx.get", return_value=_mock_response(200, {"Access-Control-Allow-Origin": "*"})):
        result = run_header_check(_check(expect_header="Access-Control-Allow-Origin", expect_value="*"))
    assert result.passed is True
    a = next(x for x in result.assertions if "header_value" in x.name)
    assert a.passed is True


def test_header_value_fail():
    with patch("httpx.get", return_value=_mock_response(200, {"Access-Control-Allow-Origin": "https://other.com"})):
        result = run_header_check(_check(expect_header="Access-Control-Allow-Origin", expect_value="*"))
    assert result.passed is False
    a = next(x for x in result.assertions if "header_value" in x.name)
    assert a.passed is False
    assert a.actual == "https://other.com"
    assert a.expected == "*"


def test_header_value_skipped_when_header_absent():
    with patch("httpx.get", return_value=_mock_response(200, {})):
        result = run_header_check(_check(expect_header="X-Missing", expect_value="something"))
    assert result.passed is False
    assert not any("header_value" in x.name for x in result.assertions)


# ---------------------------------------------------------------------------
# Header check — expect_absent
# ---------------------------------------------------------------------------

def test_header_absent_pass():
    with patch("httpx.get", return_value=_mock_response(200, {})):
        result = run_header_check(_check(expect_absent="X-Debug-Token"))
    assert result.passed is True
    a = next(x for x in result.assertions if "header_absent" in x.name)
    assert a.actual == "absent"


def test_header_absent_fail():
    with patch("httpx.get", return_value=_mock_response(200, {"X-Debug-Token": "abc123"})):
        result = run_header_check(_check(expect_absent="X-Debug-Token"))
    assert result.passed is False
    a = next(x for x in result.assertions if "header_absent" in x.name)
    assert a.actual.startswith("present")


def test_header_absent_case_insensitive():
    with patch("httpx.get", return_value=_mock_response(200, {"x-debug-token": "val"})):
        result = run_header_check(_check(expect_absent="X-Debug-Token"))
    assert result.passed is False


# ---------------------------------------------------------------------------
# Header check — network error
# ---------------------------------------------------------------------------

def test_header_check_network_error():
    with patch("httpx.get", side_effect=Exception("timeout")):
        result = run_header_check(_check(expect_header="Content-Type"))
    assert result.passed is False
    assert result.error == "timeout"
    assert result.assertions == []


# ---------------------------------------------------------------------------
# Auth check — unauthenticated rejection
# ---------------------------------------------------------------------------

def test_auth_unauth_rejected_401():
    with patch("httpx.get", return_value=_mock_response(401)):
        result = run_auth_check(_check(type="auth"))
    assert result.passed is True
    a = next(x for x in result.assertions if x.name == "unauthenticated_rejected")
    assert a.passed is True
    assert a.actual == "401"


def test_auth_unauth_rejected_403():
    with patch("httpx.get", return_value=_mock_response(403)):
        result = run_auth_check(_check(type="auth"))
    assert result.passed is True
    a = next(x for x in result.assertions if x.name == "unauthenticated_rejected")
    assert a.passed is True


def test_auth_unauth_not_rejected():
    with patch("httpx.get", return_value=_mock_response(200)):
        result = run_auth_check(_check(type="auth"))
    assert result.passed is False
    a = next(x for x in result.assertions if x.name == "unauthenticated_rejected")
    assert a.passed is False
    assert a.actual == "200"


# ---------------------------------------------------------------------------
# Auth check — authenticated access
# ---------------------------------------------------------------------------

def test_auth_with_key_passes():
    responses = [_mock_response(401), _mock_response(200)]
    with patch("httpx.get", side_effect=responses):
        result = run_auth_check(_check(type="auth", api_key="test-key-123"))
    assert result.passed is True
    assert len(result.assertions) == 2
    assert result.assertions[1].name == "authenticated_allowed"
    assert result.assertions[1].passed is True


def test_auth_with_key_fails_when_still_rejected():
    responses = [_mock_response(401), _mock_response(403)]
    with patch("httpx.get", side_effect=responses):
        result = run_auth_check(_check(type="auth", api_key="bad-key"))
    assert result.passed is False
    a = next(x for x in result.assertions if x.name == "authenticated_allowed")
    assert a.passed is False
    assert a.actual == "403"


# ---------------------------------------------------------------------------
# Auth check — env var resolution
# ---------------------------------------------------------------------------

def test_resolve_key_literal():
    assert _resolve_key("my-key") == "my-key"


def test_resolve_key_from_env(monkeypatch):
    monkeypatch.setenv("MY_API_KEY", "secret-value")
    assert _resolve_key("$MY_API_KEY") == "secret-value"


def test_resolve_key_missing_env(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    assert _resolve_key("$MISSING_KEY") == ""


def test_auth_resolves_env_var_key(monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "real-key")
    responses = [_mock_response(401), _mock_response(200)]
    with patch("httpx.get", side_effect=responses) as mock_get:
        result = run_auth_check(_check(type="auth", api_key="$TEST_API_KEY"))
    assert result.passed is True
    auth_call_headers = mock_get.call_args_list[1].kwargs.get("headers", {})
    assert auth_call_headers.get("X-Assay-Key") == "real-key"


# ---------------------------------------------------------------------------
# Auth check — network error
# ---------------------------------------------------------------------------

def test_auth_network_error_on_first_request():
    with patch("httpx.get", side_effect=Exception("refused")):
        result = run_auth_check(_check(type="auth"))
    assert result.passed is False
    assert result.error == "refused"


# ---------------------------------------------------------------------------
# Dispatcher wiring
# ---------------------------------------------------------------------------

def test_dispatcher_routes_header():
    from assay.checks.runner import run_check
    with patch("assay.checks.header.run_header_check") as mock_fn:
        mock_fn.return_value = MagicMock()
        run_check(_check(type="header"))
    mock_fn.assert_called_once()


def test_dispatcher_routes_auth():
    from assay.checks.runner import run_check
    with patch("assay.checks.auth.run_auth_check") as mock_fn:
        mock_fn.return_value = MagicMock()
        run_check(_check(type="auth"))
    mock_fn.assert_called_once()
