# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""FastAPI ingest application — POST /ingest endpoint."""

from __future__ import annotations

import base64
import html
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from grain_contracts.verification import State
from pydantic import BaseModel, field_validator, model_validator

from assay._vendor.warden import (
    WardenConfig,
    WardenMiddleware,
    clear_session_cookie,
)
from assay.formatter.formatter import format_sdk_packet
from assay.formatter.writer import write_packet
from assay.ingest.cors import DynamicCORSMiddleware
from assay.keys.require import _require_api_key

# Where unauthenticated requests are sent to authenticate. Defaults to the local
# "/login" route for dev; in production the operator points this at Gate
# (e.g. https://gate.diwata.domains/login) so auth is delegated for SSO across
# all .diwata.domains products sharing the same WARDEN_SECRET + cookie domain.
LOGIN_URL = os.environ.get("ASSAY_LOGIN_URL", "/login")
# SSO is active only when ASSAY_LOGIN_URL points at an EXTERNAL auth service (Gate).
# With the local "/login" default, delegating would self-redirect, so auth is treated
# as "not configured": protected routes return 401 (never a loop) instead of redirecting.
_SSO_ENABLED = LOGIN_URL.startswith(("http://", "https://"))

logger = logging.getLogger("assay.ingest")

app = FastAPI(title="Assay Ingest")

# Browser callers (e.g. a CRM at crm.example.com) hit POST /ingest with the custom
# X-Assay-Key header, which triggers a CORS preflight. Without CORS handling the app 405s
# the OPTIONS preflight and the browser blocks the real POST. Allowed origins come from
# the project_origins table (DynamicCORSMiddleware) so the dashboard manages them, not
# an env var — added before WardenMiddleware so it stays inner to Warden.
app.add_middleware(DynamicCORSMiddleware)

app.add_middleware(
    WardenMiddleware,
    public_paths=frozenset(
        {"/login", "/logout", "/ingest", "/ping", "/health", "/docs", "/openapi.json"}
    ),
    public_prefixes=("/status/", "/mcp", "/baselines", "/promotions"),
    login_url=LOGIN_URL if _SSO_ENABLED else None,
)

# Overridable via app.state for tests
app.state.key_store = "~/.assay/keys.json"
app.state.output_dir = "./assay-output"
app.state.store_db = "~/.assay/store.db"


def _esc(value: object) -> str:
    """HTML-escape a value before interpolating it into the inline dashboard markup.

    The dashboard renders attacker-controllable packet fields (url, summary, task_id,
    key labels) that arrive via POST /ingest, so every interpolated value must be escaped
    to prevent stored XSS into the operator's authenticated session.
    """
    return html.escape(str(value), quote=True)

from assay.api.mcp import router as _mcp_router  # noqa: E402
from assay.ingest.api import router as _dashboard_api_router  # noqa: E402
from assay.projects.api import router as _projects_router  # noqa: E402
from assay.promotions.api import router as _promotions_router  # noqa: E402

app.include_router(_mcp_router)
app.include_router(_dashboard_api_router)
app.include_router(_promotions_router)
app.include_router(_projects_router)

# Built SPA dashboard. Session-protected like every other non-public path (the
# WardenMiddleware guards everything outside public_paths/public_prefixes, and
# /dashboard is intentionally NOT in those lists). The frontend stage builds the
# compiled app into this package dir; a placeholder index ships so the mount works
# before the SPA exists.
_DASHBOARD_DIR = Path(__file__).parent / "static" / "dashboard"
_DASHBOARD_INDEX = _DASHBOARD_DIR / "index.html"


@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/dashboard/", response_class=HTMLResponse)
async def dashboard_spa_root() -> HTMLResponse:
    if _DASHBOARD_INDEX.exists():
        return HTMLResponse(_DASHBOARD_INDEX.read_text())
    raise HTTPException(status_code=404, detail="dashboard not built")


@app.get("/dashboard/{path:path}", response_model=None)
async def dashboard_spa_assets(path: str) -> FileResponse | HTMLResponse:
    candidate = (_DASHBOARD_DIR / path).resolve()
    try:
        candidate.relative_to(_DASHBOARD_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="not found") from None
    if candidate.is_file():
        return FileResponse(str(candidate))
    if _DASHBOARD_INDEX.exists():
        return HTMLResponse(_DASHBOARD_INDEX.read_text())
    raise HTTPException(status_code=404, detail="dashboard not built")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "assay"}


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
    source_ticket_id: str | None = None
    metadata: dict[str, Any] = {}
    kind: str = "report"

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

    @field_validator("kind")
    @classmethod
    def valid_kind(cls, v: str) -> str:
        if v not in ("report", "verification"):
            raise ValueError('kind must be "report" or "verification"')
        return v


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
    meta_vid = str(payload.metadata.get("verification_id", "")) or None
    packet = format_sdk_packet(payload, verification_id=meta_vid)
    packet["url"] = payload.url
    if payload.task_id:
        packet["task_id"] = payload.task_id
    source_ticket_id = payload.source_ticket_id or (
        str(payload.metadata.get("source_ticket_id", "")) or None
    )
    if source_ticket_id:
        packet["source_ticket_id"] = source_ticket_id
    output_dir = request.app.state.output_dir
    verification_id = str(packet["verification_id"])
    screenshot_path = _save_screenshot(verification_id, payload.screenshot, output_dir)
    packet["artifact_refs"] = [screenshot_path]
    _attach_diff(packet, payload.url, screenshot_path, output_dir, request.app.state.store_db)
    # `project_id` is canon (CP-007 applied), so it is stamped before write_packet so it
    # rides on the on-disk `.json` payload and stays schema-valid.
    project_id = getattr(request.state, "project_id", None)
    if project_id:
        packet["project_id"] = project_id
    write_packet(packet, output_dir)
    # `kind` is Assay-internal triage metadata, not part of the canonical Grain Sentinel
    # payload schema (assay_payload.schema.json) that write_packet's file must satisfy, so
    # it's added to the in-memory packet only after write_packet — but still before
    # _store_ingest_packet so it persists in the stored packet's `raw` JSON.
    packet["kind"] = payload.kind
    _store_ingest_packet(packet, request.app.state.store_db)
    if project_id:
        from assay.store.db import StoreError as _ProjErr
        from assay.store.db import set_packet_project

        try:
            set_packet_project(
                verification_id, project_id, Path(request.app.state.store_db).expanduser()
            )
        except _ProjErr:
            logger.warning(
                "could not stamp project_id=%s on verification_id=%s",
                project_id,
                verification_id,
            )
    if source_ticket_id:
        from assay.store.db import StoreError as _StoreError
        from assay.store.db import set_source_ticket_id

        try:
            set_source_ticket_id(
                verification_id,
                source_ticket_id,
                Path(request.app.state.store_db).expanduser(),
            )
        except _StoreError:
            logger.warning(
                "could not link verification_id=%s to source_ticket_id=%s; packet stored "
                "without the ticket link",
                verification_id,
                source_ticket_id,
            )
    if payload.kind == "report" or (payload.kind == "verification" and packet.get("outcome") == "fail"):
        from assay.store.db import StoreError, set_triage_status

        try:
            set_triage_status(verification_id, "new", Path(request.app.state.store_db).expanduser())
        except StoreError:
            logger.warning(
                "triage inbox insert failed for verification_id=%s; packet stored but "
                "did not enter the triage inbox",
                verification_id,
            )
    _wire_ticket(payload, packet, verification_id, source_ticket_id, request.app.state.store_db)
    return {"status": "accepted"}


def _wire_ticket(
    payload: "IngestPayload",
    packet: dict[str, object],
    verification_id: str,
    source_ticket_id: str | None,
    store_db: str,
) -> None:
    """Bind an ingested packet to the CP-006 durable ticket lifecycle.

    A fresh finding (`kind="report"`, no incoming ticket) mints a durable ticket in
    ``triage`` so the loop has a stable ``ASSAY-<n>`` to close back onto. A returned
    verdict (`kind="verification"`) advances the owning ticket: a PASS proposes closure
    (``in_progress -> in_review``); a FAIL holds it at ``in_progress`` because Grain
    reopens the SAME task (ticket<->task stays 1:1). All ticket writes are best-effort:
    a store failure must not fail the ingest that already persisted the packet.
    """
    from assay.store.db import (
        StoreError,
        advance_ticket,
        get_ticket,
        insert_ticket,
        set_source_ticket_id,
    )

    db = Path(store_db).expanduser()
    try:
        if payload.kind == "verification" and source_ticket_id:
            ticket = get_ticket(str(source_ticket_id), db)
            if ticket is None:
                return
            outcome = str(packet.get("outcome", ""))
            if outcome == "pass" and ticket.get("state") == State.IN_PROGRESS.value:
                advance_ticket(str(source_ticket_id), State.IN_REVIEW, db)
        elif payload.kind == "report" and not source_ticket_id:
            raw_project_id = packet.get("project_id")
            ticket_id = insert_ticket(
                title=str(packet.get("summary") or verification_id),
                severity=str(packet.get("severity") or "info"),
                priority=str(packet.get("priority") or "none"),
                db_path=db,
                project_id=str(raw_project_id) if raw_project_id is not None else None,
            )
            set_source_ticket_id(verification_id, ticket_id, db)
    except StoreError:
        logger.warning(
            "ticket wiring failed for verification_id=%s (kind=%s); packet stored but the "
            "ticket lifecycle did not advance",
            verification_id,
            payload.kind,
        )


@app.post("/ping")
async def ping(_key: str = Depends(_require_api_key)) -> dict[str, str]:
    # Lets a client (e.g. the CRM settings form) validate an API key over the exact
    # same auth + CORS path as /ingest without persisting a verification packet.
    return {"status": "ok"}


@app.get("/login")
async def login_page() -> Response:
    # Assay delegates auth to Gate (gate.diwata.domains) for SSO when configured. When
    # SSO is not configured (ASSAY_LOGIN_URL unset), do NOT self-redirect — return 503.
    if _SSO_ENABLED:
        return RedirectResponse(url=LOGIN_URL, status_code=303)
    return JSONResponse(
        {"detail": "Assay auth is not configured. Set ASSAY_LOGIN_URL to your Gate login URL."},
        status_code=503,
    )


@app.get("/logout")
async def logout() -> Response:
    # Logout is central: clearing the shared .diwata.domains session cookie signs the
    # user out of every product, then send them back to Gate's login (or "/" if unset).
    response: Response = RedirectResponse(url=LOGIN_URL if _SSO_ENABLED else "/", status_code=303)
    if os.environ.get("WARDEN_SECRET", "").strip():
        clear_session_cookie(response, WardenConfig.from_env())
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    from assay.store.db import list_baselines as _baselines
    from assay.store.db import list_packets as _list

    db_path = Path(request.app.state.store_db).expanduser()
    packets = _list(db_path)
    baselines = _baselines(db_path)
    baseline_vids = set(baselines.values())

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
        rows = '<tr><td colspan="8" style="text-align:center">no packets</td></tr>'
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
            baseline_badge = ' <span class="baseline-badge">baseline</span>' if vid in baseline_vids else ""
            rows += (
                f"<tr>"
                f'<td><a href="/packet/{_esc(vid)}">{_esc(vid[:8])}…</a>{baseline_badge}</td>'
                f'<td class="outcome-{_esc(outcome)}">{_esc(outcome)}</td>'
                f"<td>{_esc(severity)}</td>"
                f"<td>{_esc(has_screenshot)}</td>"
                f"<td>{_esc(task_id)}</td>"
                f"<td>{_esc(verified_at)}</td>"
                f"<td>{_esc(summary)}</td>"
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
.baseline-badge{{background:#1a2a1a;color:#81c784;border:1px solid #2e7d32;
border-radius:3px;padding:.1rem .4rem;font-size:.75rem;margin-left:.4rem}}
table{{border-collapse:collapse;width:100%;margin-top:1rem}}
th{{text-align:left;padding:.4rem .75rem;background:#1a1a1a;border-bottom:2px solid #333;font-size:.85rem}}
td{{padding:.35rem .75rem;border-bottom:1px solid #1e1e1e;font-size:.85rem}}
tr:hover td{{background:#141414}}
a{{color:#90caf9;text-decoration:none}}
a:hover{{text-decoration:underline}}
nav{{margin-top:2rem;font-size:.85rem}}
nav a{{margin-right:1.5rem}}
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
<nav><a href="/checks">Checks</a><a href="/keys">API Keys</a><a href="/logout">Sign out</a></nav>
</body>
</html>"""
    return HTMLResponse(content=html)


_SEVERITY_OPTIONS = ("info", "low", "medium", "error", "critical")
_PRIORITY_OPTIONS = ("low", "medium", "high", "urgent")


def _select_html(name: str, options: tuple[str, ...], current: str) -> str:
    opts = ""
    for opt in options:
        selected = " selected" if opt == current else ""
        opts += f'<option value="{_esc(opt)}"{selected}>{_esc(opt)}</option>'
    if current and current not in options:
        opts += f'<option value="{_esc(current)}" selected>{_esc(current)}</option>'
    return f'<select name="{_esc(name)}">{opts}</select>'


@app.get("/inbox", response_class=HTMLResponse)
async def inbox(request: Request) -> HTMLResponse:
    import base64 as _b64

    from assay.store.db import list_packets_page as _list_new

    db_path = Path(request.app.state.store_db).expanduser()
    packets = _list_new(db_path, triage_status="new")

    rows = ""
    if not packets:
        rows = '<tr><td colspan="6" style="text-align:center">inbox is empty</td></tr>'
    else:
        for p in packets:
            vid = str(p.get("verification_id", ""))
            url = str(p.get("url", ""))
            summary = str(p.get("summary", ""))
            user_comment = str(p.get("user_comment") or "")
            severity = str(p.get("severity") or "")
            priority = str(p.get("priority") or "")

            refs = p.get("artifact_refs", [])
            ref_list = refs if isinstance(refs, list) else []
            thumb_html = ""
            for ref in ref_list:
                ref_path = Path(str(ref))
                if ref_path.suffix == ".png" and "_diff" not in ref_path.stem and ref_path.exists():
                    thumb_b64 = _b64.b64encode(ref_path.read_bytes()).decode()
                    thumb_html = (
                        f'<img src="data:image/png;base64,{thumb_b64}" '
                        'style="max-width:160px;max-height:120px;border:1px solid #333">'
                    )
                    break
            if not thumb_html:
                thumb_html = '<span style="color:#555">no screenshot</span>'

            severity_select = _select_html("severity", _SEVERITY_OPTIONS, severity)
            priority_select = _select_html("priority", _PRIORITY_OPTIONS, priority)

            rows += (
                "<tr>"
                f"<td>{thumb_html}</td>"
                f'<td><a href="/packet/{_esc(vid)}">{_esc(vid[:8])}…</a>'
                f'<div style="color:#888;font-size:.8rem">{_esc(url)}</div></td>'
                f"<td>{_esc(user_comment)}</td>"
                f"<td>{_esc(summary)}</td>"
                "<td>"
                f'<form method="post" action="/inbox/{_esc(vid)}/triage" style="display:flex;'
                'flex-direction:column;gap:.4rem;align-items:flex-start">'
                f"{severity_select}"
                f"{priority_select}"
                '<div style="display:flex;gap:.4rem">'
                '<button name="action" value="promote" style="background:#0a1a0a;'
                "border:1px solid #2e7d32;color:#81c784;padding:.3rem .75rem;"
                "border-radius:4px;font-family:monospace;font-size:.85rem;"
                'cursor:pointer">Promote</button>'
                '<button name="action" value="dismiss" style="background:#1a0a0a;'
                "border:1px solid #c62828;color:#ef9a9a;padding:.3rem .75rem;"
                "border-radius:4px;font-family:monospace;font-size:.85rem;"
                'cursor:pointer">Dismiss</button>'
                "</div>"
                "</form>"
                "</td>"
                "</tr>"
            )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Assay — Inbox</title>
<style>
body{{font-family:monospace;background:#0d0d0d;color:#e0e0e0;margin:2rem}}
h1{{color:#fff;border-bottom:1px solid #333;padding-bottom:.5rem}}
table{{border-collapse:collapse;width:100%;margin-top:1rem}}
th{{text-align:left;padding:.4rem .75rem;background:#1a1a1a;border-bottom:2px solid #333;font-size:.85rem}}
td{{padding:.5rem .75rem;border-bottom:1px solid #1e1e1e;font-size:.85rem;vertical-align:top}}
tr:hover td{{background:#141414}}
select{{background:#0d0d0d;border:1px solid #333;color:#e0e0e0;padding:.2rem .4rem;
border-radius:4px;font-family:monospace;font-size:.8rem}}
a{{color:#90caf9;text-decoration:none}}
a:hover{{text-decoration:underline}}
nav{{margin-top:2rem;font-size:.85rem}}
nav a{{margin-right:1.5rem}}
</style>
</head>
<body>
<h1>Assay — Triage Inbox</h1>
<table>
<thead>
<tr>
<th>screenshot</th><th>packet</th><th>user comment</th><th>summary</th><th>triage</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
<nav><a href="/">Packets</a><a href="/checks">Checks</a><a href="/keys">API Keys</a><a href="/logout">Sign out</a></nav>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.post("/inbox/{verification_id}/triage")
async def inbox_triage(
    verification_id: str,
    request: Request,
    action: str = Form(...),
    severity: str = Form(default=""),
    priority: str = Form(default=""),
) -> RedirectResponse:
    from assay.store.db import get_packet as _get_packet
    from assay.store.db import set_priority as _set_priority
    from assay.store.db import set_severity as _set_severity
    from assay.store.db import set_triage_status as _set_triage_status

    db_path = Path(request.app.state.store_db).expanduser()
    packet = _get_packet(verification_id, db_path)
    if packet is None:
        raise HTTPException(status_code=404, detail="packet not found")
    if severity:
        _set_severity(verification_id, severity, db_path)
    if priority:
        _set_priority(verification_id, priority, db_path)
    if action == "promote":
        _set_triage_status(verification_id, "promoted", db_path)
        _advance_owning_ticket(packet, State.TODO, db_path)
    elif action == "dismiss":
        _set_triage_status(verification_id, "dismissed", db_path)
        _advance_owning_ticket(packet, State.CANCELED, db_path)
    else:
        raise HTTPException(status_code=400, detail="action must be promote or dismiss")
    return RedirectResponse("/inbox", status_code=303)


def _advance_owning_ticket(packet: dict[str, object], target: State, db_path: Path) -> None:
    """Advance a packet's owning ticket out of ``triage`` when it is triaged.

    Only fires when the ticket is still in ``triage`` (the sole legal source for both
    ``todo`` and ``canceled``), so a re-triage of the same packet is an idempotent no-op
    rather than an illegal transition. Best-effort: never fail the operator's action if
    the ticket write fails.
    """
    from assay.store.db import StoreError, advance_ticket, get_ticket

    ticket_id = packet.get("source_ticket_id")
    if not ticket_id:
        return
    try:
        ticket = get_ticket(str(ticket_id), db_path)
        if ticket is not None and ticket.get("state") == State.TRIAGE.value:
            advance_ticket(str(ticket_id), target, db_path)
    except StoreError:
        logger.warning("could not advance ticket %s to %s", ticket_id, target.value)


@app.get("/checks", response_class=HTMLResponse)
async def checks_dashboard(request: Request) -> HTMLResponse:
    from assay.store.db import init_db as _init
    from assay.store.db import list_check_results as _list_checks

    db_path = Path(request.app.state.store_db).expanduser()
    _init(db_path)
    results = _list_checks(db_path)

    rows = ""
    if not results:
        rows = '<tr><td colspan="6" style="text-align:center">no checks run yet</td></tr>'
    else:
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            status_class = "pass" if r["passed"] else "fail"
            from typing import cast as _cast2
            assertions = _cast2(list[dict[str, object]], r.get("assertions") or [])
            failed = [a for a in assertions if not a.get("passed")]
            detail = "; ".join(f"{a['name']}: {a['actual']}" for a in failed) if failed else (
                "all pass" if assertions else "—"
            )
            ts = str(r.get("checked_at", ""))[:19]
            rows += (
                f"<tr>"
                f'<td>{_esc(r["check_id"])}</td>'
                f'<td>{_esc(r["check_type"])}</td>'
                f'<td style="max-width:260px;overflow:hidden;text-overflow:ellipsis">{_esc(r["target"])}</td>'
                f'<td class="outcome-{status_class}">{status}</td>'
                f"<td>{_esc(detail)}</td>"
                f"<td>{_esc(ts)}</td>"
                f"</tr>"
            )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Assay — Checks</title>
<style>
body{{font-family:monospace;background:#0d0d0d;color:#e0e0e0;margin:2rem}}
h1{{color:#fff;border-bottom:1px solid #333;padding-bottom:.5rem}}
.outcome-pass{{color:#4caf50}}
.outcome-fail{{color:#f44336}}
table{{border-collapse:collapse;width:100%;margin-top:1rem}}
th{{text-align:left;padding:.4rem .75rem;background:#1a1a1a;border-bottom:2px solid #333;font-size:.85rem}}
td{{padding:.35rem .75rem;border-bottom:1px solid #1e1e1e;font-size:.85rem}}
tr:hover td{{background:#141414}}
a{{color:#90caf9;text-decoration:none}}
a:hover{{text-decoration:underline}}
nav{{margin-top:2rem;font-size:.85rem}}
nav a{{margin-right:1.5rem}}
</style>
</head>
<body>
<h1>Assay — Check Results</h1>
<table>
<thead>
<tr>
<th>check_id</th><th>type</th><th>target</th><th>status</th><th>detail</th><th>checked_at</th>
</tr>
</thead>
<tbody>
{rows}
</tbody>
</table>
<nav><a href="/">Packets</a><a href="/keys">API Keys</a><a href="/logout">Sign out</a></nav>
</body>
</html>"""
    return HTMLResponse(content=html)


_SLIDER_CSS = """
.diff-tabs{display:flex;gap:.5rem;margin-bottom:.75rem}
.diff-tab{background:#1a1a1a;border:1px solid #333;color:#aaa;padding:.3rem .85rem;
border-radius:4px;font-family:monospace;font-size:.8rem;cursor:pointer}
.diff-tab.active{background:#2a2a2a;border-color:#555;color:#e0e0e0}
.diff-tab:hover{background:#222}
.diff-stats{font-size:.85rem;color:#aaa;margin:.4rem 0 .75rem}
.slider-wrap{position:relative;overflow:hidden;max-width:900px;
cursor:col-resize;user-select:none;border:1px solid #333;line-height:0}
.slider-wrap img.sl-base{display:block;width:100%}
.sl-after{position:absolute;top:0;left:0;bottom:0;overflow:hidden;width:50%}
.sl-after img{display:block;width:100%}
.sl-handle{position:absolute;top:0;left:50%;height:100%;width:3px;
background:rgba(255,255,255,.85);transform:translateX(-50%);
pointer-events:none;display:flex;align-items:center;justify-content:center}
.sl-knob{width:28px;height:28px;border-radius:50%;background:#fff;
display:flex;align-items:center;justify-content:center;
color:#333;font-size:.9rem;box-shadow:0 2px 6px rgba(0,0,0,.6);pointer-events:none}
.sbs-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;max-width:900px}
.sbs-grid p{margin:.25rem 0 .4rem;font-size:.8rem;color:#888}
.sbs-grid img{width:100%;border:1px solid #333}
"""

_SLIDER_JS = """
(function(){
  var c=document.getElementById('sl-c');
  if(!c)return;
  var after=document.getElementById('sl-after');
  var handle=document.getElementById('sl-handle');
  var afterImg=after.querySelector('img');
  var drag=false;
  function pct(e){
    var r=c.getBoundingClientRect();
    var x=(e.touches?e.touches[0].clientX:e.clientX)-r.left;
    return Math.max(0,Math.min(100,x/r.width*100));
  }
  function set(p){
    after.style.width=p+'%';
    handle.style.left=p+'%';
    afterImg.style.width=c.offsetWidth+'px';
  }
  c.addEventListener('mousedown',function(e){drag=true;set(pct(e));e.preventDefault();});
  window.addEventListener('mouseup',function(){drag=false;});
  window.addEventListener('mousemove',function(e){if(drag)set(pct(e));});
  c.addEventListener('touchstart',function(e){drag=true;set(pct(e.touches[0]));},{passive:true});
  window.addEventListener('touchend',function(){drag=false;});
  window.addEventListener('touchmove',function(e){if(drag){set(pct(e));e.preventDefault();}},{passive:false});
  function init(){set(50);afterImg.style.width=c.offsetWidth+'px';}
  if(document.readyState==='loading')window.addEventListener('DOMContentLoaded',init);else init();
  window.addEventListener('resize',function(){if(!drag)set(50);});
})();
function showDiffTab(id){
  document.querySelectorAll('.diff-tab').forEach(function(b){b.classList.remove('active');});
  document.querySelectorAll('.diff-panel').forEach(function(p){p.style.display='none';});
  document.getElementById(id).style.display='';
  event.target.classList.add('active');
}
"""


def _build_slider_html(
    baseline_b64: str,
    candidate_b64: str,
    diff_b64: str,
    stats_p: str,
) -> str:
    diff_tab_btn = (
        "<button class='diff-tab' onclick=\"showDiffTab('dp-diff')\">Highlight</button>"
        if diff_b64
        else ""
    )
    diff_tab_panel = (
        f"<div id='dp-diff' class='diff-panel' style='display:none'>"
        f"<img src='data:image/png;base64,{diff_b64}' "
        f"style='max-width:900px;width:100%;border:1px solid #333'>"
        f"</div>"
        if diff_b64
        else ""
    )
    return (
        f"<style>{_SLIDER_CSS}</style>"
        "<h2>Diff vs Baseline</h2>"
        f"{stats_p}"
        "<div class='diff-tabs'>"
        "<button class='diff-tab active' onclick=\"showDiffTab('dp-slider')\">Slider</button>"
        f"{diff_tab_btn}"
        "<button class='diff-tab' onclick=\"showDiffTab('dp-sbs')\">Side by side</button>"
        "</div>"
        "<div id='dp-slider' class='diff-panel'>"
        "<div class='slider-wrap' id='sl-c'>"
        f"<img class='sl-base' src='data:image/png;base64,{baseline_b64}' alt='baseline'>"
        "<div class='sl-after' id='sl-after'>"
        f"<img src='data:image/png;base64,{candidate_b64}' alt='candidate'>"
        "</div>"
        "<div class='sl-handle' id='sl-handle'><div class='sl-knob'>⟺</div></div>"
        "</div>"
        "<p style='font-size:.75rem;color:#666;margin-top:.4rem'>"
        "← drag to compare baseline (left) vs new capture (right)</p>"
        "</div>"
        f"{diff_tab_panel}"
        "<div id='dp-sbs' class='diff-panel' style='display:none'>"
        "<div class='sbs-grid'>"
        f"<div><p>Before (baseline)</p>"
        f"<img src='data:image/png;base64,{baseline_b64}' alt='baseline'></div>"
        f"<div><p>After (new capture)</p>"
        f"<img src='data:image/png;base64,{candidate_b64}' alt='candidate'></div>"
        "</div></div>"
        f"<script>{_SLIDER_JS}</script>"
    )


@app.get("/packet/{verification_id}", response_class=HTMLResponse)
async def packet_detail(verification_id: str, request: Request) -> HTMLResponse:
    import base64 as _b64
    import json as _json

    from assay.store.db import list_packets as _list

    db_path = Path(request.app.state.store_db).expanduser()
    all_packets = _list(db_path)
    packet = next((p for p in all_packets if str(p.get("verification_id", "")) == verification_id), None)

    if packet is None:
        html_404 = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<title>Not found — Assay</title>"
            "<style>body{font-family:monospace;background:#0d0d0d;color:#e0e0e0;margin:2rem}"
            "a{color:#90caf9}</style></head>"
            f"<body><h1>404 — packet not found</h1><p>{_esc(verification_id)}</p>"
            "<p><a href='/'>← back to dashboard</a></p></body></html>"
        )
        return HTMLResponse(content=html_404, status_code=404)

    fields_html = ""
    skip = {"artifact_refs", "raw", "diff_result"}
    for key, val in packet.items():
        if key in skip:
            continue
        fields_html += f"<dt>{_esc(key)}</dt><dd>{_esc(val)}</dd>"

    refs = packet.get("artifact_refs", [])
    ref_list = refs if isinstance(refs, list) else []
    candidate_b64 = ""
    for ref in ref_list:
        p_path = Path(str(ref))
        if p_path.suffix == ".png" and "_diff" not in p_path.stem and p_path.exists():
            candidate_b64 = _b64.b64encode(p_path.read_bytes()).decode()
            break

    screenshot_html = ""
    diff_html = ""
    diff_result = packet.get("diff_result")

    if isinstance(diff_result, dict):
        diff_pct = diff_result.get("diff_pct", 0)
        changed = diff_result.get("changed_pixels", 0)
        total = diff_result.get("total_pixels", 0)
        diff_img_path = Path(str(diff_result.get("diff_image_path", "")))
        diff_b64 = ""
        if diff_img_path.exists():
            diff_b64 = _b64.b64encode(diff_img_path.read_bytes()).decode()

        baseline_b64 = ""
        packet_url = str(packet.get("url", ""))
        if packet_url:
            from assay.store.db import get_baseline_for_url as _get_bl

            bl_packet = _get_bl(packet_url, db_path)
            if bl_packet:
                bl_refs = bl_packet.get("artifact_refs", [])
                for br in (bl_refs if isinstance(bl_refs, list) else []):
                    bp = Path(str(br))
                    if bp.suffix == ".png" and "_diff" not in bp.stem and bp.exists():
                        baseline_b64 = _b64.b64encode(bp.read_bytes()).decode()
                        break

        stats_p = (
            f'<p class="diff-stats">{diff_pct}% changed '
            f"({changed} / {total} pixels)</p>"
        )

        if baseline_b64 and candidate_b64:
            diff_html = _build_slider_html(
                baseline_b64, candidate_b64, diff_b64, stats_p
            )
        else:
            diff_img_tag = (
                f'<img src="data:image/png;base64,{diff_b64}" '
                f'style="max-width:100%;border:1px solid #333;margin-top:.5rem">'
                if diff_b64
                else ""
            )
            diff_html = (
                "<h2>Diff vs Baseline</h2>"
                f"{stats_p}"
                f"{diff_img_tag}"
            )
    elif candidate_b64:
        screenshot_html = (
            "<h2>Screenshot</h2>"
            f'<img src="data:image/png;base64,{candidate_b64}" '
            'style="max-width:100%;border:1px solid #333">'
        )

    raw_str = str(packet.get("raw", ""))
    try:
        raw_pretty = _json.dumps(_json.loads(raw_str), indent=2)
    except Exception:
        raw_pretty = raw_str

    from assay.store.db import list_baselines as _baselines

    db_path_for_baseline = Path(request.app.state.store_db).expanduser()
    baselines = _baselines(db_path_for_baseline)
    baseline_vids = set(baselines.values())
    is_baseline = verification_id in baseline_vids
    review_status = str(packet.get("review_status") or "")

    if is_baseline:
        baseline_action = (
            '<span style="color:#81c784;font-size:.85rem">✓ This is the current baseline for this URL</span>'
        )
    else:
        baseline_action = (
            f"<form method='post' action='/packet/{_esc(verification_id)}/set-baseline' style='display:inline'>"
            "<button style='background:#1a2a1a;border:1px solid #2e7d32;color:#81c784;"
            "padding:.3rem .75rem;border-radius:4px;font-family:monospace;font-size:.85rem;"
            "cursor:pointer'>Set as baseline</button></form>"
        )

    has_diff = isinstance(diff_result, dict)
    review_buttons = ""
    if has_diff and not is_baseline:
        review_buttons = (
            f"<form method='post' action='/packet/{_esc(verification_id)}/approve' "
            "style='display:inline;margin-left:.75rem'>"
            "<button style='background:#0a1a0a;border:1px solid #2e7d32;color:#81c784;"
            "padding:.3rem .75rem;border-radius:4px;font-family:monospace;font-size:.85rem;"
            "cursor:pointer'>✓ Approve</button></form>"
            f"<form method='post' action='/packet/{_esc(verification_id)}/reject' "
            "style='display:inline;margin-left:.5rem'>"
            "<button style='background:#1a0a0a;border:1px solid #c62828;color:#ef9a9a;"
            "padding:.3rem .75rem;border-radius:4px;font-family:monospace;font-size:.85rem;"
            "cursor:pointer'>✗ Reject</button></form>"
        )

    review_badge = ""
    if review_status == "approved":
        review_badge = (
            " <span style='background:#0a1a0a;color:#81c784;border:1px solid #2e7d32;"
            "border-radius:3px;padding:.1rem .4rem;font-size:.75rem'>approved</span>"
        )
    elif review_status == "rejected":
        review_badge = (
            " <span style='background:#1a0a0a;color:#ef9a9a;border:1px solid #c62828;"
            "border-radius:3px;padding:.1rem .4rem;font-size:.75rem'>regression</span>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Packet {_esc(verification_id[:8])} — Assay</title>
<style>
body{{font-family:monospace;background:#0d0d0d;color:#e0e0e0;margin:2rem}}
h1,h2{{color:#fff;border-bottom:1px solid #333;padding-bottom:.4rem}}
dl{{display:grid;grid-template-columns:max-content 1fr;gap:.3rem 1.5rem;margin:1rem 0}}
dt{{color:#aaa;font-size:.85rem}}
dd{{margin:0;font-size:.85rem}}
pre{{background:#111;padding:1rem;border-radius:4px;overflow-x:auto;font-size:.8rem}}
a{{color:#90caf9;text-decoration:none}}
a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<p><a href="/">← dashboard</a></p>
<h1>Packet {_esc(verification_id[:8])}…{review_badge}</h1>
<p>{baseline_action}{review_buttons}</p>
<dl>{fields_html}</dl>
{screenshot_html}
{diff_html}
<h2>Raw</h2>
<pre>{_esc(raw_pretty)}</pre>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.post("/packet/{verification_id}/set-baseline")
async def set_packet_baseline(verification_id: str, request: Request) -> RedirectResponse:
    from assay.store.db import StoreError
    from assay.store.db import set_baseline as _set

    db_path = Path(request.app.state.store_db).expanduser()
    try:
        _set(verification_id, db_path)
    except StoreError:
        pass
    return RedirectResponse(url=f"/packet/{verification_id}", status_code=303)


@app.post("/packet/{verification_id}/approve")
async def approve_packet(verification_id: str, request: Request) -> RedirectResponse:
    from assay.store.db import StoreError
    from assay.store.db import set_baseline as _set
    from assay.store.db import set_review_status as _review

    db_path = Path(request.app.state.store_db).expanduser()
    try:
        _set(verification_id, db_path)
    except StoreError:
        pass
    try:
        _review(verification_id, "approved", db_path)
    except StoreError:
        pass
    return RedirectResponse(url=f"/packet/{verification_id}", status_code=303)


@app.post("/packet/{verification_id}/reject")
async def reject_packet(verification_id: str, request: Request) -> RedirectResponse:
    from assay.store.db import StoreError
    from assay.store.db import set_review_status as _review

    db_path = Path(request.app.state.store_db).expanduser()
    try:
        _review(verification_id, "rejected", db_path)
    except StoreError:
        pass
    return RedirectResponse(url=f"/packet/{verification_id}", status_code=303)


@app.get("/status/{verification_id}")
async def verification_status(verification_id: str, request: Request) -> dict[str, object]:
    from assay.store.db import list_packets as _list

    db_path = Path(request.app.state.store_db).expanduser()
    all_packets = _list(db_path)
    packet = next((p for p in all_packets if str(p.get("verification_id", "")) == verification_id), None)

    if packet is None:
        from fastapi.responses import JSONResponse
        return JSONResponse(content={"status": "not_found"}, status_code=404)  # type: ignore[return-value]

    return {
        "status": "complete",
        "verification_id": verification_id,
        "outcome": str(packet.get("outcome", "")),
        "verified_at": str(packet.get("verified_at", "")),
        "task_id": str(packet.get("task_id") or ""),
        "summary": str(packet.get("summary", "")),
    }


# ---------------------------------------------------------------------------
# Agent baseline management — API-key authenticated, headless (no dashboard)
# ---------------------------------------------------------------------------


class BaselineRequest(BaseModel):
    verification_id: str

    @field_validator("verification_id")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("verification_id must be a non-empty string")
        return v


@app.get("/baselines")
async def baselines_list(
    request: Request,
    _key: str = Depends(_require_api_key),
) -> dict[str, object]:
    from assay.api import service

    return {"baselines": service.list_baselines(store_db=request.app.state.store_db)}


@app.post("/baselines/set")
async def baselines_set(
    request: Request,
    body: BaselineRequest,
    _key: str = Depends(_require_api_key),
) -> dict[str, object]:
    from assay.api import service

    try:
        return service.set_baseline(body.verification_id, store_db=request.app.state.store_db)
    except service.ServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/baselines/approve")
async def baselines_approve(
    request: Request,
    body: BaselineRequest,
    _key: str = Depends(_require_api_key),
) -> dict[str, object]:
    from assay.api import service

    try:
        return service.approve_baseline(body.verification_id, store_db=request.app.state.store_db)
    except service.ServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/baselines/reject")
async def baselines_reject(
    request: Request,
    body: BaselineRequest,
    _key: str = Depends(_require_api_key),
) -> dict[str, object]:
    from assay.api import service

    try:
        return service.reject_baseline(body.verification_id, store_db=request.app.state.store_db)
    except service.ServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


_KEYS_STYLE = (
    "body{font-family:monospace;background:#0d0d0d;color:#e0e0e0;margin:2rem}"
    "h1{color:#fff;border-bottom:1px solid #333;padding-bottom:.5rem}"
    "a{color:#90caf9;text-decoration:none}"
    "table{border-collapse:collapse;width:100%;margin:1rem 0}"
    "th{text-align:left;padding:.4rem .75rem;background:#1a1a1a;border-bottom:2px solid #333;font-size:.85rem}"
    "td{padding:.35rem .75rem;border-bottom:1px solid #1e1e1e;font-size:.85rem}"
    "form.inline{display:inline}"
    "button{background:#2a2a2a;border:1px solid #444;color:#e0e0e0;padding:.3rem .75rem;"
    "border-radius:4px;font-family:monospace;font-size:.85rem;cursor:pointer}"
    "button:hover{background:#333}"
    "button.danger{border-color:#c62828;color:#ef9a9a}"
    "button.danger:hover{background:#1a0000}"
    ".create-form{margin:1.5rem 0;display:flex;gap:.75rem;align-items:center}"
    ".create-form input{background:#0d0d0d;border:1px solid #333;color:#e0e0e0;"
    "padding:.4rem .6rem;border-radius:4px;font-family:monospace;font-size:.85rem}"
    ".create-form input:focus{outline:none;border-color:#555}"
    ".new-key{background:#0a1a0a;border:1px solid #2e7d32;border-radius:4px;"
    "padding:.75rem 1rem;margin:1rem 0;font-size:.9rem}"
    ".new-key .label{color:#81c784;font-size:.8rem;margin-bottom:.4rem}"
    ".new-key code{color:#a5d6a7;word-break:break-all}"
    ".revoked{color:#555}"
)


def _keys_page(
    key_store: str,
    new_key: str = "",
    new_label: str = "",
) -> str:
    from assay.keys.store import list_keys as _list

    keys = _list(key_store)
    new_key_html = ""
    if new_key:
        new_key_html = (
            "<div class='new-key'>"
            f"<div class='label'>New key for <strong>{_esc(new_label)}</strong> "
            "— copy it now, it won't be shown again</div>"
            f"<code>{_esc(new_key)}</code>"
            "</div>"
        )

    rows = ""
    active = [k for k in keys if not k.get("revoked")]
    if not active:
        rows = '<tr><td colspan="3" style="text-align:center;color:#555">no active keys</td></tr>'
    else:
        for k in active:
            kid = str(k["id"])
            label = str(k["label"])
            created = str(k["created_at"])[:10]
            rows += (
                f"<tr>"
                f"<td>{_esc(label)}</td>"
                f"<td>{_esc(created)}</td>"
                f"<td>"
                f"<form class='inline' method='post' action='/keys/{_esc(kid)}/revoke'>"
                f"<button class='danger' type='submit'>Revoke</button>"
                f"</form>"
                f"</td>"
                f"</tr>"
            )

    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<title>Assay — API Keys</title>"
        f"<style>{_KEYS_STYLE}</style></head><body>"
        "<h1><a href='/'>Assay</a> / API Keys</h1>"
        f"{new_key_html}"
        "<form class='create-form' method='post' action='/keys'>"
        "<input type='text' name='label' placeholder='Key label (e.g. crm-prod)' required>"
        "<button type='submit'>Create key</button>"
        "</form>"
        "<table><thead><tr><th>label</th><th>created</th><th></th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        "<p style='margin-top:2rem'><a href='/logout'>Sign out</a></p>"
        "</body></html>"
    )


@app.get("/keys", response_class=HTMLResponse)
async def keys_list(request: Request) -> HTMLResponse:
    return HTMLResponse(_keys_page(request.app.state.key_store))


@app.post("/keys", response_model=None)
async def keys_create(
    request: Request,
    label: str = Form(...),
) -> HTMLResponse:
    from assay.keys.store import create_key as _create

    raw = _create(request.app.state.key_store, label.strip() or None)
    return HTMLResponse(_keys_page(request.app.state.key_store, new_key=raw, new_label=label.strip()))


@app.post("/keys/{key_id}/revoke")
async def keys_revoke(key_id: str, request: Request) -> RedirectResponse:
    from assay.keys.store import KeyStoreError
    from assay.keys.store import revoke_key as _revoke

    try:
        _revoke(request.app.state.key_store, key_id)
    except KeyStoreError:
        pass
    return RedirectResponse(url="/keys", status_code=303)


def _attach_diff(
    packet: dict[str, object],
    url: str,
    screenshot_path: str,
    output_dir: str,
    store_db: str,
) -> None:
    """Run pixel diff against baseline if one exists for the URL. Mutates packet in-place."""
    from pathlib import Path as _Path

    from assay.diff.engine import DiffError
    from assay.diff.engine import diff_images as _diff
    from assay.store.db import get_baseline_for_url as _get_baseline
    from assay.store.db import init_db as _init

    try:
        db_path = _Path(store_db).expanduser()
        _init(db_path)
        baseline = _get_baseline(url, db_path)
        if baseline is None:
            return
        refs = baseline.get("artifact_refs", [])
        ref_list = refs if isinstance(refs, list) else []
        baseline_png = next((r for r in ref_list if str(r).endswith(".png")), None)
        if not baseline_png:
            return
        diff_path = _Path(output_dir) / f"{packet['verification_id']}_diff.png"
        result = _diff(_Path(str(baseline_png)), _Path(screenshot_path), diff_path)
        packet["diff_result"] = {
            "changed_pixels": result.changed_pixels,
            "total_pixels": result.total_pixels,
            "diff_pct": result.diff_pct,
            "diff_image_path": result.diff_image_path,
        }
        from typing import cast as _cast2

        existing = _cast2(list[object], packet.get("artifact_refs", []))
        packet["artifact_refs"] = list(existing) + [result.diff_image_path]
    except (DiffError, Exception):
        pass


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
