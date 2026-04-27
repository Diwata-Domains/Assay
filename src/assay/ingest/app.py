"""FastAPI ingest application — POST /ingest endpoint."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, field_validator, model_validator

from assay.formatter.formatter import format_sdk_packet
from assay.formatter.writer import write_packet
from assay.keys.store import verify_key

app = FastAPI(title="Assay Ingest")

# Overridable via app.state for tests
app.state.key_store = "~/.assay/keys.json"
app.state.output_dir = "./assay-output"


class Viewport(BaseModel):
    width: int
    height: int

    @model_validator(mode="after")
    def positive_dimensions(self) -> "Viewport":
        if self.width <= 0 or self.height <= 0:
            raise ValueError("viewport width and height must be positive integers")
        return self


class IngestPayload(BaseModel):
    captured_at: str
    url: str
    viewport: Viewport
    user_agent: str
    screenshot: str
    user_comment: str | None = None
    task_id: str | None = None
    metadata: dict[str, Any] = {}

    @field_validator("captured_at")
    @classmethod
    def non_empty_captured_at(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("captured_at must be a non-empty ISO 8601 string")
        return v

    @field_validator("url")
    @classmethod
    def non_empty_url(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("url must be a non-empty string")
        return v

    @field_validator("user_agent")
    @classmethod
    def non_empty_user_agent(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("user_agent must be a non-empty string")
        return v

    @field_validator("screenshot")
    @classmethod
    def valid_base64(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("screenshot must be a non-empty base64-encoded string")
        try:
            base64.b64decode(v, validate=True)
        except Exception as exc:
            raise ValueError("screenshot must be valid base64") from exc
        return v


def _require_api_key(request: Request, x_assay_key: str | None = Header(default=None)) -> str:
    if not x_assay_key:
        raise HTTPException(status_code=401, detail="missing X-Assay-Key header")
    store = request.app.state.key_store
    if not verify_key(store, x_assay_key):
        raise HTTPException(status_code=401, detail="invalid or revoked API key")
    return x_assay_key


def _save_screenshot(verification_id: str, screenshot_b64: str, output_dir: str) -> str:
    """Decode base64 screenshot and write to <output_dir>/<verification_id>.png. Returns file path."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{verification_id}.png"
    path.write_bytes(base64.b64decode(screenshot_b64))
    return str(path)


@app.post("/ingest")
async def ingest(
    request: Request,
    payload: IngestPayload,
    _key: str = Depends(_require_api_key),
) -> dict[str, str]:
    packet = format_sdk_packet(payload)
    if payload.task_id:
        packet["task_id"] = payload.task_id
    output_dir = request.app.state.output_dir
    verification_id = str(packet["verification_id"])
    screenshot_path = _save_screenshot(verification_id, payload.screenshot, output_dir)
    packet["artifact_refs"] = [screenshot_path]
    write_packet(packet, output_dir)
    return {"status": "accepted"}
