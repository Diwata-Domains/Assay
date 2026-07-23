"""Session-authed Projects CRUD API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from assay._vendor.warden import WardenConfig, issue_token
from assay.ingest.app import app
from assay.keys.store import verify_key_project
from assay.store.db import get_project_for_origin, list_projects

_SECRET = "x" * 32
_EMAIL = "admin@test.com"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    app.state.key_store = str(tmp_path / "keys.json")
    app.state.store_db = str(tmp_path / "store.db")
    app.state.output_dir = str(tmp_path / "output")
    c = TestClient(app)
    c.cookies.set("warden_session", issue_token(_EMAIL, WardenConfig(secret=_SECRET)))
    return c


def test_unauthenticated_projects_request_is_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WARDEN_SECRET", _SECRET)
    app.state.store_db = str(tmp_path / "store.db")
    anon = TestClient(app, follow_redirects=False)
    r = anon.get("/api/projects")
    # ASSAY_LOGIN_URL is unset in tests -> login_url None -> Warden denies with 401 JSON.
    assert r.status_code == 401


def test_create_project_returns_key_once(client: TestClient, tmp_path: Path) -> None:
    r = client.post("/api/projects", json={"name": "LC CRM", "origin": "https://crm.example"})
    assert r.status_code == 200
    body = r.json()
    assert body["project"]["name"] == "LC CRM"
    pid = body["project"]["id"]
    assert body["api_key"]
    match = verify_key_project(str(tmp_path / "keys.json"), body["api_key"])
    assert match is not None and match.project_id == pid
    assert (
        get_project_for_origin("https://crm.example", db_path=Path(str(tmp_path / "store.db")))
        == pid
    )


def test_list_projects(client: TestClient) -> None:
    client.post("/api/projects", json={"name": "A", "origin": "https://a.example"})
    r = client.get("/api/projects")
    assert r.status_code == 200
    assert any(p["name"] == "A" for p in r.json()["projects"])


def test_add_origin(client: TestClient) -> None:
    pid = client.post(
        "/api/projects", json={"name": "Acme", "origin": "https://acme.example"}
    ).json()["project"]["id"]
    r = client.post(f"/api/projects/{pid}/origins", json={"origin": "https://acme2.example"})
    assert r.status_code == 200
    assert r.json()["origin"]["origin"] == "https://acme2.example"


def test_duplicate_origin_on_add_route_is_rejected(client: TestClient) -> None:
    client.post("/api/projects", json={"name": "A", "origin": "https://dup.example"})
    pid = client.post(
        "/api/projects", json={"name": "B", "origin": "https://b.example"}
    ).json()["project"]["id"]
    r = client.post(f"/api/projects/{pid}/origins", json={"origin": "https://dup.example"})
    assert r.status_code == 409


def test_duplicate_origin_on_create_leaves_no_orphan_project(
    client: TestClient, tmp_path: Path
) -> None:
    # Registering an already-taken origin at create time must 409 WITHOUT persisting a
    # nameless, origin-less, key-less orphan project row.
    client.post("/api/projects", json={"name": "First", "origin": "https://taken.example"})
    before = len(list_projects(db_path=Path(str(tmp_path / "store.db"))))
    r = client.post("/api/projects", json={"name": "Second", "origin": "https://taken.example"})
    assert r.status_code == 409
    after = len(list_projects(db_path=Path(str(tmp_path / "store.db"))))
    assert after == before


def test_mint_additional_project_key(client: TestClient, tmp_path: Path) -> None:
    pid = client.post(
        "/api/projects", json={"name": "apex", "origin": "https://apex.example"}
    ).json()["project"]["id"]
    r = client.post(f"/api/projects/{pid}/keys", json={"label": "second"})
    assert r.status_code == 200
    match = verify_key_project(str(tmp_path / "keys.json"), r.json()["api_key"])
    assert match is not None and match.project_id == pid


def test_get_projects_includes_active_keys(client: TestClient) -> None:
    client.post("/api/projects", json={"name": "K", "origin": "https://k.example"})
    projects = client.get("/api/projects").json()["projects"]
    proj = next(p for p in projects if p["name"] == "K")
    assert proj["keys"], "each project should surface its active keys"
    assert "id" in proj["keys"][0] and "label" in proj["keys"][0]


def test_delete_origin_route_unbinds(client: TestClient, tmp_path: Path) -> None:
    created = client.post(
        "/api/projects", json={"name": "D", "origin": "https://d.example"}
    ).json()
    pid = created["project"]["id"]
    client.post(f"/api/projects/{pid}/origins", json={"origin": "https://d2.example"})
    r = client.request(
        "DELETE", f"/api/projects/{pid}/origins", json={"origin": "https://d2.example"}
    )
    assert r.status_code == 200
    assert r.json()["deleted"]["origin"] == "https://d2.example"
    db = Path(str(tmp_path / "store.db"))
    assert get_project_for_origin("https://d2.example", db_path=db) is None
    # the original create-origin is untouched
    assert get_project_for_origin("https://d.example", db_path=db) == pid


def test_delete_unknown_origin_is_404(client: TestClient) -> None:
    pid = client.post(
        "/api/projects", json={"name": "E", "origin": "https://e.example"}
    ).json()["project"]["id"]
    r = client.request(
        "DELETE", f"/api/projects/{pid}/origins", json={"origin": "https://nope.example"}
    )
    assert r.status_code == 404


def test_revoke_project_key_route(client: TestClient, tmp_path: Path) -> None:
    created = client.post(
        "/api/projects", json={"name": "R", "origin": "https://r.example"}
    ).json()
    pid = created["project"]["id"]
    raw = created["api_key"]
    assert verify_key_project(str(tmp_path / "keys.json"), raw) is not None
    key_id = next(
        p for p in client.get("/api/projects").json()["projects"] if p["id"] == pid
    )["keys"][0]["id"]
    r = client.post(f"/api/projects/{pid}/keys/{key_id}/revoke")
    assert r.status_code == 200
    assert r.json()["revoked"] == key_id
    # security-critical: the revoked key no longer verifies
    assert verify_key_project(str(tmp_path / "keys.json"), raw) is None


def test_revoke_foreign_key_is_404(client: TestClient) -> None:
    # A key minted for project A cannot be revoked through project B's route.
    a = client.post("/api/projects", json={"name": "A", "origin": "https://a.example"}).json()
    b = client.post("/api/projects", json={"name": "B", "origin": "https://b.example"}).json()
    a_pid = a["project"]["id"]
    b_pid = b["project"]["id"]
    a_key_id = next(
        p for p in client.get("/api/projects").json()["projects"] if p["id"] == a_pid
    )["keys"][0]["id"]
    r = client.post(f"/api/projects/{b_pid}/keys/{a_key_id}/revoke")
    assert r.status_code == 404
