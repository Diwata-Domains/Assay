"""Dynamic, DB-backed CORS: an origin is allowed iff it is registered in project_origins."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from assay._vendor.warden import WardenConfig, issue_token
from assay.ingest.app import app
from assay.store.db import add_project_origin, init_db, insert_project

_SECRET = "x" * 32
_EMAIL = "admin@test.com"


def _preflight(origin: str) -> dict[str, str]:
    return {
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-assay-key",
    }


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    db = str(tmp_path / "store.db")
    app.state.store_db = db
    app.state.key_store = str(tmp_path / "keys.json")
    app.state.output_dir = str(tmp_path / "output")
    init_db(Path(db))
    pid = insert_project("CRM", db_path=Path(db))
    add_project_origin(pid, "https://crm.example", db_path=Path(db))
    from assay.ingest.cors import invalidate_origin_cache

    invalidate_origin_cache()
    c = TestClient(app)
    c.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return c


def test_registered_origin_preflight_is_allowed(client: TestClient) -> None:
    r = client.options("/ingest", headers=_preflight("https://crm.example"))
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "https://crm.example"
    allow_headers = r.headers["access-control-allow-headers"].lower()
    assert "x-assay-key" in allow_headers and "content-type" in allow_headers
    assert "POST" in r.headers["access-control-allow-methods"]


def test_unregistered_origin_is_not_reflected(client: TestClient) -> None:
    r = client.options("/ingest", headers=_preflight("https://evil.example"))
    assert r.headers.get("access-control-allow-origin") != "https://evil.example"


def test_cors_inert_on_authed_api_request_with_origin(client: TestClient) -> None:
    # A normal (non-preflight) authed GET carrying an Origin header must still succeed;
    # DynamicCORSMiddleware only reflects headers, it never blocks the request.
    r = client.get("/api/projects", headers={"Origin": "https://crm.example"})
    assert r.status_code == 200
    assert "projects" in r.json()


def test_newly_added_origin_is_allowed_without_restart(client: TestClient) -> None:
    r = client.options("/ingest", headers=_preflight("https://new.example"))
    assert r.headers.get("access-control-allow-origin") != "https://new.example"
    pid = client.post(
        "/api/projects", json={"name": "New", "origin": "https://new.example"}
    ).json()["project"]["id"]
    assert pid
    r2 = client.options("/ingest", headers=_preflight("https://new.example"))
    assert r2.headers["access-control-allow-origin"] == "https://new.example"


def test_deleted_origin_is_no_longer_allowed(client: TestClient) -> None:
    # crm.example is registered in the fixture; deleting it via the CRUD must invalidate the
    # CORS cache so the next preflight is refused — no redeploy.
    r = client.options("/ingest", headers=_preflight("https://crm.example"))
    assert r.headers["access-control-allow-origin"] == "https://crm.example"
    projects = client.get("/api/projects").json()["projects"]
    pid = next(p["id"] for p in projects if "https://crm.example" in p["origins"])
    d = client.request(
        "DELETE", f"/api/projects/{pid}/origins", json={"origin": "https://crm.example"}
    )
    assert d.status_code == 200
    r2 = client.options("/ingest", headers=_preflight("https://crm.example"))
    assert r2.headers.get("access-control-allow-origin") != "https://crm.example"


def test_cache_is_isolated_per_db(tmp_path: Path) -> None:
    from assay.ingest.cors import invalidate_origin_cache, origin_allowed

    invalidate_origin_cache()
    db_a = tmp_path / "a.db"
    db_b = tmp_path / "b.db"
    init_db(db_a)
    init_db(db_b)
    pid = insert_project("A", db_path=db_a)
    add_project_origin(pid, "https://shared.example", db_path=db_a)
    # allowed against db_a, but a different DB with no such origin must resolve independently
    assert origin_allowed(str(db_a), "https://shared.example") is True
    assert origin_allowed(str(db_b), "https://shared.example") is False
