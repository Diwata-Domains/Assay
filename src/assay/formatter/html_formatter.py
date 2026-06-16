# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""HTML report formatter — produces a single self-contained file with inline screenshots."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import cast

_STYLE = """
body { font-family: system-ui, sans-serif; margin: 2rem; color: #1a1a1a; background: #f9f9f9; }
h1 { font-size: 1.4rem; margin-bottom: 0.25rem; }
.summary { font-size: 0.9rem; color: #555; margin-bottom: 1.5rem; }
.summary span { font-weight: bold; }
.pass { color: #16a34a; }
.fail { color: #dc2626; }
.inconclusive { color: #ca8a04; }
table { border-collapse: collapse; width: 100%; background: #fff;
        border-radius: 6px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
th { background: #f1f5f9; text-align: left; padding: 0.6rem 0.8rem;
     font-size: 0.8rem; color: #475569; border-bottom: 1px solid #e2e8f0; }
td { padding: 0.6rem 0.8rem; font-size: 0.8rem; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
tr:last-child td { border-bottom: none; }
.vid { font-family: monospace; font-size: 0.7rem; color: #64748b; }
img.thumb { max-width: 200px; max-height: 120px; border: 1px solid #e2e8f0; border-radius: 3px; display: block; }
"""


def _outcome_class(outcome: str) -> str:
    return outcome if outcome in ("pass", "fail", "inconclusive") else ""


def _embed_screenshot(refs: list[object]) -> str:
    for ref in refs:
        path = Path(str(ref))
        if path.suffix.lower() == ".png" and path.exists():
            data = base64.b64encode(path.read_bytes()).decode()
            return f'<img class="thumb" src="data:image/png;base64,{data}" alt="screenshot">'
    return ""


def render_html(packets: list[dict[str, object]]) -> str:
    total = len(packets)
    passed = sum(1 for p in packets if p.get("outcome") == "pass")
    failed = sum(1 for p in packets if p.get("outcome") == "fail")
    inconclusive = total - passed - failed

    rows: list[str] = []
    for p in packets:
        vid = str(p.get("verification_id", ""))
        outcome = str(p.get("outcome", ""))
        severity = str(p.get("severity", ""))
        task_id = str(p.get("task_id") or "—")
        verified_at = str(p.get("verified_at") or "")[:19].replace("T", " ")
        summary = str(p.get("summary", ""))
        refs = cast(list[object], p.get("artifact_refs", []))
        screenshot_html = _embed_screenshot(refs)
        css = _outcome_class(outcome)
        rows.append(
            f"<tr>"
            f'<td class="vid">{vid}</td>'
            f'<td class="{css}"><strong>{outcome}</strong></td>'
            f"<td>{severity}</td>"
            f"<td>{task_id}</td>"
            f"<td>{verified_at}</td>"
            f"<td>{summary}</td>"
            f"<td>{screenshot_html}</td>"
            f"</tr>"
        )

    rows_html = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Assay Report</title>
<style>{_STYLE}</style>
</head>
<body>
<h1>Assay Report</h1>
<p class="summary">
  <span>{total}</span> total &nbsp;|&nbsp;
  <span class="pass">{passed}</span> passed &nbsp;|&nbsp;
  <span class="fail">{failed}</span> failed &nbsp;|&nbsp;
  <span class="inconclusive">{inconclusive}</span> inconclusive
</p>
<table>
<thead>
<tr>
  <th>Verification ID</th>
  <th>Outcome</th>
  <th>Severity</th>
  <th>Task ID</th>
  <th>Verified At</th>
  <th>Summary</th>
  <th>Screenshot</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</body>
</html>
"""
