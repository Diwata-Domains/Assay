"""Gate client helpers — the product side of the one-login handoff.

Vendored verbatim from packages/warden/warden/gate.py (Assay ships to PyPI as
``assay-kit`` and cannot depend on the unpublished ``warden`` package, so the
whole auth lib lives under ``assay._vendor.warden``). Keep this in lockstep with
the source when the shared gate contract changes.

one_login_spec.md §4: a product never builds login UI. It redirects the browser
to the Gate (``begin_login_url``), the Gate authenticates and redirects back to
the product's REGISTERED redirect URI with a one-time code, and the product
redeems that code server-side (``exchange_code``) for the visitor's identity —
then mints its own session with its existing machinery.

Host portability is law: every URL here derives from the single
``GATE_PUBLIC_ORIGIN`` config value. Switching the gate host (gate.diwata.domains
→ diwata.id) is a config change, never a code change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from .config import WardenConfigError
from .exceptions import WardenError

_EXCHANGE_PATH = "/sso/exchange"
_LOGIN_PATH = "/login"


class GateExchangeError(WardenError):
    """The Gate refused (or failed) a one-time-code exchange."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class GateClientConfig:
    """A registered Gate client's connection settings.

    Attributes:
        gate_origin: The ONE session-bearing gate host, scheme included, no
            trailing slash (e.g. ``https://gate.diwata.domains``).
        client_id: This product's registered client id (e.g. ``assay``).
        client_secret: Shared secret authenticating server-side exchange calls.
    """

    gate_origin: str
    client_id: str
    client_secret: str

    @classmethod
    def from_env(cls, client_id: str | None = None) -> GateClientConfig:
        """Load from env vars: GATE_PUBLIC_ORIGIN, GATE_CLIENT_ID, GATE_CLIENT_SECRET.

        ``client_id`` parameter, when given, wins over the env var — products
        with a fixed identity pass it explicitly.

        Secret lookup prefers the per-client name GATE_CLIENT_SECRET_<ID>
        (uppercased) and falls back to the generic GATE_CLIENT_SECRET — the
        operator stack shares one .env across services, so two clients on the
        same box need per-client names (found 2026-08-04 when Conclave's flip
        claimed the generic name Diwa would also read).
        """
        origin = os.environ.get("GATE_PUBLIC_ORIGIN", "").strip().rstrip("/")
        if not origin:
            raise WardenConfigError("GATE_PUBLIC_ORIGIN env var is required")
        cid = (client_id or os.environ.get("GATE_CLIENT_ID", "")).strip()
        if not cid:
            raise WardenConfigError("GATE_CLIENT_ID env var (or client_id argument) is required")
        per_client = f"GATE_CLIENT_SECRET_{cid.upper().replace('-', '_')}"
        secret = os.environ.get(per_client, "").strip() or os.environ.get("GATE_CLIENT_SECRET", "").strip()
        if not secret:
            raise WardenConfigError("GATE_CLIENT_SECRET env var is required")
        return cls(gate_origin=origin, client_id=cid, client_secret=secret)


def begin_login_url(
    config: GateClientConfig, redirect_uri: str, state: str | None = None
) -> str:
    """The Gate login URL to send the browser to.

    ``redirect_uri`` must exactly match one of the client's registered URIs —
    the Gate refuses anything else (spec §6.3).
    """
    params: dict[str, str] = {"client_id": config.client_id, "redirect_uri": redirect_uri}
    if state:
        params["state"] = state
    return f"{config.gate_origin}{_LOGIN_PATH}?{urlencode(params)}"


async def exchange_code(
    config: GateClientConfig,
    code: str,
    redirect_uri: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Redeem a one-time code server-side for the visitor's identity.

    Returns the Gate's identity payload (at least ``sub`` and ``email``).
    Raises GateExchangeError when the Gate refuses the code or the client
    credentials, or on a malformed response.
    """
    async with httpx.AsyncClient(transport=transport, timeout=timeout) as client:
        try:
            response = await client.post(
                f"{config.gate_origin}{_EXCHANGE_PATH}",
                json={
                    "client_id": config.client_id,
                    "client_secret": config.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )
        except httpx.HTTPError as exc:
            raise GateExchangeError(f"gate unreachable: {exc}") from exc

    if response.status_code != 200:
        detail = ""
        try:
            detail = str(response.json().get("detail", ""))
        except Exception:  # noqa: BLE001 — any non-JSON error body
            detail = response.text[:200]
        raise GateExchangeError(
            f"exchange refused ({response.status_code}): {detail}",
            status_code=response.status_code,
        )

    try:
        payload: dict[str, Any] = response.json()
    except ValueError as exc:
        raise GateExchangeError("malformed exchange response: not JSON") from exc
    if not isinstance(payload, dict) or "sub" not in payload:
        raise GateExchangeError("malformed exchange response: missing 'sub'")
    return payload
