# SPDX-FileCopyrightText: 2024-2026 Shaznay Sison
# SPDX-License-Identifier: AGPL-3.0-only

"""Telemetry emitter — opt-in, fire-and-forget event emission for Pulse.

Assay only emits typed, versioned :class:`TelemetryEvent` envelopes at key
moments (today: ``verification.completed``). Transport and aggregation are
Pulse's responsibility. The envelope shape matches Grain's exactly
(``{event_type, version, timestamp, payload}``) so Pulse accepts it verbatim
over HTTP (``pulse serve``) or by draining a queued ``.jsonl`` (``pulse drain``).

``emit(event)`` is the single entry point and is strictly side-band: it NEVER
raises, NEVER changes caller control flow, and NEVER alters the verification's
timing. Emission only happens when telemetry is explicitly enabled
(``ASSAY_TELEMETRY_ENDPOINT`` env var is set OR a ``[telemetry]`` block with
``enabled = true`` in assay.toml). Default off → nothing is emitted and no queue
file is written.

Non-blocking by construction: the only work ``emit`` does on the caller's thread
is the cheap, local gate check and event serialization. The network POST (and
its on-disk queue fallback) run on a short-lived daemon thread, so
``run_verification`` returns without ever waiting on the network — even when a
configured endpoint is slow or unreachable.

When enabled, the event is POSTed to the configured Pulse endpoint. If no
endpoint is configured, or the endpoint is unreachable, the event is appended to
``.assay/telemetry_queue.jsonl`` (one JSON object per line) so a later
``pulse drain`` can pick it up. The payload carries counts and identifiers only —
no PII, no screenshots, no artifacts.
"""

from __future__ import annotations

import dataclasses
import json
import os
import threading
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Environment override for the Pulse ingest URL. Setting it also turns telemetry
# on (opt-in via env), independent of the assay.toml block.
ENDPOINT_ENV_VAR = "ASSAY_TELEMETRY_ENDPOINT"

# Event type identifiers — never rename without bumping the event version, since
# Pulse consumers key off these strings.
EVENT_VERIFICATION_COMPLETED = "verification.completed"

# Current schema version for emitted events. Bump on any breaking payload change.
TELEMETRY_EVENT_VERSION = 1

_QUEUE_FILE = "telemetry_queue.jsonl"
_ASSAY_DIR = ".assay"
# Kept short so even a stalled drain thread tears down quickly; it runs off the
# hot path so this timeout never affects the verification's latency.
_POST_TIMEOUT_SECONDS = 2.0

# Tracks in-flight dispatch threads so ``flush`` can join them. A daemon thread
# never blocks interpreter exit, so this is only consulted by ``flush``.
_PENDING_LOCK = threading.Lock()
_PENDING: list[threading.Thread] = []


@dataclass
class TelemetryEvent:
    """A single typed, versioned telemetry event.

    ``event_type`` is one of the module-level ``EVENT_*`` constants, ``version``
    is the schema version, ``timestamp`` is an ISO-8601 UTC string, and
    ``payload`` carries event-specific fields (no PII; identifiers and counts
    only). The field order/shape matches Grain's envelope exactly.
    """

    event_type: str
    version: int = TELEMETRY_EVENT_VERSION
    timestamp: str = ""
    payload: dict[str, object] = field(default_factory=dict)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _config_block(config_path: str | None) -> dict[str, object]:
    """Return the ``[telemetry]`` table from assay.toml, or ``{}``. Never raises.

    Resolves the config the same way :mod:`assay.config` does (explicit path,
    then ./assay.toml, then ~/.assay/config.toml). ``[telemetry]`` is read here
    rather than via the typed loader so an unknown-section guard there never
    rejects the opt-in block.
    """
    try:
        import tomllib

        if config_path is not None:
            path: Path | None = Path(config_path)
            if path is not None and not path.exists():
                return {}
        else:
            local = Path("assay.toml")
            global_ = Path.home() / ".assay" / "config.toml"
            path = local if local.exists() else (global_ if global_.exists() else None)
        if path is None:
            return {}
        raw = tomllib.loads(path.read_text())
        block = raw.get("telemetry", {})
        return block if isinstance(block, dict) else {}
    except Exception:
        return {}


def is_enabled(config_path: str | None = None) -> bool:
    """Return True when telemetry is opt-in enabled. Never raises.

    Enabled when ``ASSAY_TELEMETRY_ENDPOINT`` is set OR ``[telemetry]
    enabled = true`` in assay.toml. Default off.
    """
    try:
        if os.environ.get(ENDPOINT_ENV_VAR, "").strip():
            return True
        return bool(_config_block(config_path).get("enabled", False))
    except Exception:
        return False


def _resolve_endpoint(config_path: str | None) -> str:
    """Return the configured Pulse endpoint (env wins over assay.toml)."""
    env_endpoint = os.environ.get(ENDPOINT_ENV_VAR, "").strip()
    if env_endpoint:
        return env_endpoint
    endpoint = _config_block(config_path).get("endpoint", "")
    return str(endpoint).strip() if isinstance(endpoint, str) else ""


def emit(event: TelemetryEvent, *, config_path: str | None = None) -> None:
    """Emit one telemetry event. Fire-and-forget; NEVER raises; NEVER blocks.

    No-op when telemetry is disabled (the default). When enabled, the network
    POST (and its on-disk queue fallback) are dispatched on a short-lived daemon
    thread so the caller returns immediately — instrumentation never alters the
    timing of the verification. On any POST failure (no endpoint, transport
    error) the event is appended to ``.assay/telemetry_queue.jsonl`` for a later
    ``pulse drain``.
    """
    try:
        if not is_enabled(config_path):
            return

        if not event.timestamp:
            event.timestamp = _now_iso()

        record = dataclasses.asdict(event)
        endpoint = _resolve_endpoint(config_path)

        _dispatch(endpoint, record)
    except Exception:
        # Telemetry is strictly side-band — never propagate any failure.
        return


def _dispatch(endpoint: str, record: dict[str, object]) -> None:
    """Run the POST-or-queue work on a short-lived daemon thread (never blocks)."""
    thread = threading.Thread(
        target=_deliver,
        args=(endpoint, record),
        name="assay-telemetry",
        daemon=True,
    )
    with _PENDING_LOCK:
        _PENDING.append(thread)
    thread.start()


def _deliver(endpoint: str, record: dict[str, object]) -> None:
    """Off-thread delivery: POST, falling back to the on-disk queue. Never raises."""
    try:
        if endpoint and _try_post(endpoint, record):
            return
        _append_to_queue(record)
    except Exception:
        # Strictly side-band — swallow everything on the background thread too.
        return
    finally:
        current = threading.current_thread()
        with _PENDING_LOCK:
            if current in _PENDING:
                _PENDING.remove(current)


def flush(timeout: float | None = 5.0) -> None:
    """Join any in-flight dispatch threads. Never raises.

    Makes the otherwise-async emission path deterministic (tests, or a future
    drain that wants to wait for delivery). Production instrumentation never
    calls this — the dispatch threads are daemons and clean up on their own.
    """
    with _PENDING_LOCK:
        pending = list(_PENDING)
    for thread in pending:
        try:
            thread.join(timeout)
        except Exception:
            continue


def _try_post(endpoint: str, record: dict[str, object]) -> bool:
    """POST the event JSON to the Pulse endpoint. Return True on success.

    Dependency-free (stdlib urllib) and best-effort: any transport/HTTP error
    returns False so the caller falls back to the on-disk queue.
    """
    try:
        data = json.dumps(record).encode("utf-8")
        request = urllib.request.Request(endpoint, data=data, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header("User-Agent", "assay-cli")
        with urllib.request.urlopen(request, timeout=_POST_TIMEOUT_SECONDS):  # noqa: S310
            return True
    except Exception:
        return False


def _append_to_queue(record: dict[str, object]) -> None:
    """Append one JSON line to ``.assay/telemetry_queue.jsonl`` (best effort)."""
    assay_dir = Path(_ASSAY_DIR)
    assay_dir.mkdir(exist_ok=True)
    queue_path = assay_dir / _QUEUE_FILE
    with queue_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# ── Typed event builders (versioned contract lives here) ───────────────────────

def make_verification_completed_event(
    verification_id: str,
    target: str,
    *,
    passed: bool,
    checks_total: int,
    checks_passed: int,
) -> TelemetryEvent:
    """Build a versioned verification.completed event.

    Payload is counts + identifiers only (no PII, no screenshots/artifacts):
    ``verification_id``, ``target``, ``passed``, ``checks_total``,
    ``checks_passed``.
    """
    return TelemetryEvent(
        event_type=EVENT_VERIFICATION_COMPLETED,
        version=TELEMETRY_EVENT_VERSION,
        timestamp=_now_iso(),
        payload={
            "verification_id": verification_id,
            "target": target,
            "passed": passed,
            "checks_total": checks_total,
            "checks_passed": checks_passed,
        },
    )
