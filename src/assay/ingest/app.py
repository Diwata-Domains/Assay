# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""FastAPI ingest application — POST /ingest endpoint."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Form, Header, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, field_validator, model_validator
from warden import WardenConfig, WardenMiddleware, clear_session_cookie, issue_token, set_session_cookie

from assay.formatter.formatter import format_sdk_packet
from assay.formatter.writer import write_packet
from assay.keys.store import verify_key

app = FastAPI(title="Assay Ingest")
app.add_middleware(
    WardenMiddleware,
    public_paths=frozenset({"/login", "/logout", "/ingest", "/health", "/docs", "/openapi.json"}),
    public_prefixes=("/status/", "/mcp", "/baselines"),
)

# Overridable via app.state for tests
app.state.key_store = "~/.assay/keys.json"
app.state.output_dir = "./assay-output"
app.state.store_db = "~/.assay/store.db"

from assay.api.mcp import router as _mcp_router  # noqa: E402

app.include_router(_mcp_router)


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
    meta_vid = str(payload.metadata.get("verification_id", "")) or None
    packet = format_sdk_packet(payload, verification_id=meta_vid)
    packet["url"] = payload.url
    if payload.task_id:
        packet["task_id"] = payload.task_id
    output_dir = request.app.state.output_dir
    verification_id = str(packet["verification_id"])
    screenshot_path = _save_screenshot(verification_id, payload.screenshot, output_dir)
    packet["artifact_refs"] = [screenshot_path]
    _attach_diff(packet, payload.url, screenshot_path, output_dir, request.app.state.store_db)
    write_packet(packet, output_dir)
    _store_ingest_packet(packet, request.app.state.store_db)
    return {"status": "accepted"}


_LOGIN_STYLE = (
    "body{font-family:monospace;background:#0d0d0d;color:#e0e0e0;"
    "display:flex;align-items:center;justify-content:center;height:100vh;margin:0}"
    ".box{background:#1a1a1a;border:1px solid #333;border-radius:6px;padding:2rem 2.5rem;width:320px}"
    "h1{color:#fff;margin:0 0 1.5rem;font-size:1.2rem;border-bottom:1px solid #333;padding-bottom:.75rem}"
    "label{display:block;font-size:.8rem;color:#999;margin-bottom:.25rem}"
    "input{width:100%;box-sizing:border-box;background:#0d0d0d;border:1px solid #333;color:#e0e0e0;"
    "padding:.5rem .6rem;border-radius:4px;font-family:monospace;font-size:.9rem;margin-bottom:1rem}"
    "input:focus{outline:none;border-color:#555}"
    "button{width:100%;background:#2a2a2a;border:1px solid #444;color:#e0e0e0;padding:.6rem;"
    "border-radius:4px;font-family:monospace;font-size:.9rem;cursor:pointer}"
    "button:hover{background:#333}"
    ".error{color:#f44336;font-size:.8rem;margin-bottom:1rem}"
)


def _login_page(error: str = "", next_url: str = "") -> str:
    error_html = f'<p class="error">{error}</p>' if error else ""
    next_field = f"<input type='hidden' name='next' value='{next_url}'>" if next_url else ""
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<title>Assay — Login</title>"
        f"<style>{_LOGIN_STYLE}</style></head><body>"
        "<div class='box'><h1>Assay</h1>"
        f"{error_html}"
        "<form method='post' action='/login'>"
        f"{next_field}"
        "<label>Email</label><input type='email' name='email' required autofocus>"
        "<label>Password</label><input type='password' name='password' required>"
        "<button type='submit'>Sign in</button>"
        "</form></div></body></html>"
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(next: str = Query(default="")) -> HTMLResponse:
    return HTMLResponse(_login_page(next_url=next))


@app.post("/login", response_model=None)
async def login_submit(
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form(default=""),
) -> HTMLResponse | RedirectResponse:
    from assay.auth.admin import (
        get_admin_email,
        get_admin_password_hash,
        verify_password,
    )

    try:
        admin_email = get_admin_email()
        admin_hash = get_admin_password_hash()
    except RuntimeError:
        msg = "Server misconfigured — ASSAY_ADMIN_* env vars not set."
        return HTMLResponse(_login_page(msg, next_url=next), status_code=500)

    if email.strip().lower() != admin_email.lower() or not verify_password(password, admin_hash):
        return HTMLResponse(_login_page("Invalid email or password.", next_url=next), status_code=401)

    cfg = WardenConfig.from_env()
    token = issue_token(email.strip().lower(), cfg)
    redirect_to = next.strip() or "/"
    response: RedirectResponse = RedirectResponse(url=redirect_to, status_code=303)
    set_session_cookie(response, token, cfg)
    return response


@app.get("/logout")
async def logout() -> RedirectResponse:
    response: RedirectResponse = RedirectResponse(url="/login", status_code=303)
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
                f'<td><a href="/packet/{vid}">{vid[:8]}…</a>{baseline_badge}</td>'
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
                f'<td>{r["check_id"]}</td>'
                f'<td>{r["check_type"]}</td>'
                f'<td style="max-width:260px;overflow:hidden;text-overflow:ellipsis">{r["target"]}</td>'
                f'<td class="outcome-{status_class}">{status}</td>'
                f"<td>{detail}</td>"
                f"<td>{ts}</td>"
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
            f"<body><h1>404 — packet not found</h1><p>{verification_id}</p>"
            "<p><a href='/'>← back to dashboard</a></p></body></html>"
        )
        return HTMLResponse(content=html_404, status_code=404)

    fields_html = ""
    skip = {"artifact_refs", "raw", "diff_result"}
    for key, val in packet.items():
        if key in skip:
            continue
        fields_html += f"<dt>{key}</dt><dd>{val}</dd>"

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
            f"<form method='post' action='/packet/{verification_id}/set-baseline' style='display:inline'>"
            "<button style='background:#1a2a1a;border:1px solid #2e7d32;color:#81c784;"
            "padding:.3rem .75rem;border-radius:4px;font-family:monospace;font-size:.85rem;"
            "cursor:pointer'>Set as baseline</button></form>"
        )

    has_diff = isinstance(diff_result, dict)
    review_buttons = ""
    if has_diff and not is_baseline:
        review_buttons = (
            f"<form method='post' action='/packet/{verification_id}/approve' style='display:inline;margin-left:.75rem'>"
            "<button style='background:#0a1a0a;border:1px solid #2e7d32;color:#81c784;"
            "padding:.3rem .75rem;border-radius:4px;font-family:monospace;font-size:.85rem;"
            "cursor:pointer'>✓ Approve</button></form>"
            f"<form method='post' action='/packet/{verification_id}/reject' style='display:inline;margin-left:.5rem'>"
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
<title>Packet {verification_id[:8]} — Assay</title>
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
<h1>Packet {verification_id[:8]}…{review_badge}</h1>
<p>{baseline_action}{review_buttons}</p>
<dl>{fields_html}</dl>
{screenshot_html}
{diff_html}
<h2>Raw</h2>
<pre>{raw_pretty}</pre>
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
            f"<div class='label'>New key for <strong>{new_label}</strong> — copy it now, it won't be shown again</div>"
            f"<code>{new_key}</code>"
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
                f"<td>{label}</td>"
                f"<td>{created}</td>"
                f"<td>"
                f"<form class='inline' method='post' action='/keys/{kid}/revoke'>"
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
