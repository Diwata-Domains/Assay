"""FastAPI ingest application — POST /ingest endpoint."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator, model_validator

from assay.formatter.formatter import format_sdk_packet
from assay.formatter.writer import write_packet
from assay.keys.store import verify_key

app = FastAPI(title="Assay Ingest")

# Overridable via app.state for tests
app.state.key_store = "~/.assay/keys.json"
app.state.output_dir = "./assay-output"
app.state.store_db = "~/.assay/store.db"


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
    _store_ingest_packet(packet, request.app.state.store_db)
    return {"status": "accepted"}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    from assay.store.db import list_packets as _list

    db_path = Path(request.app.state.store_db).expanduser()
    packets = _list(db_path)

    total = len(packets)
    counts: dict[str, int] = {}
    for p in packets:
        outcome = str(p.get("outcome", "unknown"))
        counts[outcome] = counts.get(outcome, 0) + 1

    summary_parts = [f"<span>{total} total</span>"]
    for outcome in ("pass", "fail", "inconclusive"):
        n = counts.get(outcome, 0)
        summary_parts.append(f'<span class="outcome-{outcome}">{n} {outcome}</span>')

    rows = ""
    if not packets:
        rows = '<tr><td colspan="7" style="text-align:center">no packets</td></tr>'
    else:
        for p in packets:
            vid = str(p.get("verification_id", ""))
            outcome = str(p.get("outcome", ""))
            severity = str(p.get("severity", ""))
            verified_at = str(p.get("verified_at", ""))[:10]
            summary = str(p.get("summary", ""))
            task_id = str(p.get("task_id") or "")
            refs = p.get("artifact_refs", [])
            ref_list = refs if isinstance(refs, list) else []
            has_screenshot = "yes" if any(str(r).endswith(".png") for r in ref_list) else "no"
            rows += (
                f"<tr>"
                f'<td><a href="/packet/{vid}">{vid[:8]}…</a></td>'
                f'<td class="outcome-{outcome}">{outcome}</td>'
                f"<td>{severity}</td>"
                f"<td>{has_screenshot}</td>"
                f"<td>{task_id}</td>"
                f"<td>{verified_at}</td>"
                f"<td>{summary}</td>"
                f"</tr>"
            )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Assay Dashboard</title>
<style>
body{{font-family:monospace;background:#0d0d0d;color:#e0e0e0;margin:2rem}}
h1{{color:#fff;border-bottom:1px solid #333;padding-bottom:.5rem}}
.summary{{display:flex;gap:1.5rem;margin:1rem 0;font-size:.95rem}}
.summary span{{padding:.25rem .75rem;background:#1a1a1a;border-radius:4px}}
.outcome-pass{{color:#4caf50}}
.outcome-fail{{color:#f44336}}
.outcome-inconclusive{{color:#ff9800}}
table{{border-collapse:collapse;width:100%;margin-top:1rem}}
th{{text-align:left;padding:.4rem .75rem;background:#1a1a1a;border-bottom:2px solid #333;font-size:.85rem}}
td{{padding:.35rem .75rem;border-bottom:1px solid #1e1e1e;font-size:.85rem}}
tr:hover td{{background:#141414}}
a{{color:#90caf9;text-decoration:none}}
a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<h1>Assay Dashboard</h1>
<div class="summary">{''.join(summary_parts)}</div>
<table>
<thead>
<tr>
<th>verification_id</th><th>outcome</th><th>severity</th>
<th>screenshot</th><th>task_id</th><th>verified_at</th><th>summary</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
</body>
</html>"""
    return HTMLResponse(content=html)


def _store_ingest_packet(packet: dict[str, object], store_db: str) -> None:
    from pathlib import Path as _Path

    from assay.store.db import init_db
    from assay.store.db import insert_packet as _insert

    db_path = _Path(store_db).expanduser()
    try:
        init_db(db_path)
        _insert(packet, db_path)
    except Exception:
        pass
