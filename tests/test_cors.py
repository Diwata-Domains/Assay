"""Tests for CORS preflight handling on the ingest app."""

from __future__ import annotations

from fastapi.testclient import TestClient

from assay.ingest.app import app

_PREFLIGHT_HEADERS = {
    "Origin": "https://crm.example.com",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type,x-assay-key",
}


def test_ingest_preflight_allows_cross_origin_post() -> None:
    client = TestClient(app)
    r = client.options("/ingest", headers=_PREFLIGHT_HEADERS)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "https://crm.example.com"
    allow_headers = r.headers["access-control-allow-headers"].lower()
    assert "x-assay-key" in allow_headers
    assert "content-type" in allow_headers
    assert "POST" in r.headers["access-control-allow-methods"]


def test_disallowed_origin_is_not_reflected() -> None:
    client = TestClient(app)
    r = client.options(
        "/ingest",
        headers={**_PREFLIGHT_HEADERS, "Origin": "https://evil.example"},
    )
    assert r.headers.get("access-control-allow-origin") != "https://evil.example"
