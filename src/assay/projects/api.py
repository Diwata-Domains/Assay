# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Operator-only Projects CRUD API.

Session-authenticated by OMISSION from the WardenMiddleware public lists — there is no
per-route dependency here (the same rule as the /api dashboard router). Never add
/api/projects to public_paths/public_prefixes, and never attach _require_api_key.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator

from assay.keys.store import KeyStoreError, create_key, list_keys, revoke_key
from assay.store.db import (
    StoreError,
    add_project_origin,
    delete_project_origin,
    get_project,
    get_project_for_origin,
    insert_project,
    list_project_origins,
    list_projects,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _db_path(request: Request) -> Path:
    return Path(request.app.state.store_db).expanduser()


class CreateProjectBody(BaseModel):
    name: str
    origin: str

    @field_validator("name", "origin")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must be non-empty")
        return v.strip()


class AddOriginBody(BaseModel):
    origin: str

    @field_validator("origin")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must be non-empty")
        return v.strip()


class CreateKeyBody(BaseModel):
    label: str | None = None


@router.get("")
async def list_projects_route(request: Request) -> dict[str, object]:
    db = _db_path(request)
    try:
        projects = list_projects(db)
        active_keys = [k for k in list_keys(request.app.state.key_store) if not k.get("revoked")]
        for p in projects:
            p["origins"] = [o["origin"] for o in list_project_origins(str(p["id"]), db)]
            p["keys"] = [
                {"id": k["id"], "label": k["label"], "created_at": k["created_at"]}
                for k in active_keys
                if k.get("project_id") == p["id"]
            ]
    except StoreError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"projects": projects}


@router.post("")
async def create_project_route(request: Request, body: CreateProjectBody) -> dict[str, object]:
    db = _db_path(request)
    try:
        if get_project_for_origin(body.origin, db_path=db) is not None:
            raise HTTPException(status_code=409, detail=f"origin already registered: {body.origin}")
        pid = insert_project(body.name, db_path=db)
        add_project_origin(pid, body.origin, db_path=db)
    except StoreError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    raw = create_key(request.app.state.key_store, label=body.name, project_id=pid)
    project = get_project(pid, db)
    return {"project": project, "api_key": raw}


@router.post("/{project_id}/origins")
async def add_origin_route(
    request: Request, project_id: str, body: AddOriginBody
) -> dict[str, object]:
    db = _db_path(request)
    if get_project(project_id, db) is None:
        raise HTTPException(status_code=404, detail=f"project {project_id} not found")
    try:
        add_project_origin(project_id, body.origin, db_path=db)
    except StoreError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"origin": {"origin": body.origin, "project_id": project_id}}


@router.post("/{project_id}/keys")
async def create_project_key_route(
    request: Request, project_id: str, body: CreateKeyBody
) -> dict[str, object]:
    db = _db_path(request)
    if get_project(project_id, db) is None:
        raise HTTPException(status_code=404, detail=f"project {project_id} not found")
    raw = create_key(request.app.state.key_store, label=body.label, project_id=project_id)
    return {"api_key": raw}


@router.delete("/{project_id}/origins")
async def delete_origin_route(
    request: Request, project_id: str, body: AddOriginBody
) -> dict[str, object]:
    db = _db_path(request)
    if get_project(project_id, db) is None:
        raise HTTPException(status_code=404, detail=f"project {project_id} not found")
    try:
        delete_project_origin(project_id, body.origin, db_path=db)
    except StoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": {"origin": body.origin, "project_id": project_id}}


@router.post("/{project_id}/keys/{key_id}/revoke")
async def revoke_project_key_route(
    request: Request, project_id: str, key_id: str
) -> dict[str, object]:
    db = _db_path(request)
    if get_project(project_id, db) is None:
        raise HTTPException(status_code=404, detail=f"project {project_id} not found")
    store = request.app.state.key_store
    match = next((k for k in list_keys(store) if str(k["id"]) == key_id), None)
    if match is None or match.get("project_id") != project_id:
        raise HTTPException(
            status_code=404, detail=f"key {key_id} not found for project {project_id}"
        )
    try:
        revoke_key(store, key_id)
    except KeyStoreError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"revoked": key_id}
