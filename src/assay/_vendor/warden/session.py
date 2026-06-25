"""Session cookie helpers."""

from __future__ import annotations

from starlette.responses import Response

from .config import WardenConfig


def set_session_cookie(response: Response, token: str, config: WardenConfig) -> None:
    """Set the Warden session cookie on a response.

    The cookie is HttpOnly, uses the configured domain and SameSite policy,
    and has a max-age matching the token TTL.
    """
    kwargs: dict[str, object] = {
        "key": config.cookie_name,
        "value": token,
        "httponly": True,
        "max_age": config.ttl_seconds,
        "samesite": config.samesite,
        "secure": config.secure_cookie,
    }
    if config.cookie_domain:
        kwargs["domain"] = config.cookie_domain
    response.set_cookie(**kwargs)  # type: ignore[arg-type]


def clear_session_cookie(response: Response, config: WardenConfig) -> None:
    """Delete the Warden session cookie (logout)."""
    kwargs: dict[str, object] = {"key": config.cookie_name, "httponly": True}
    if config.cookie_domain:
        kwargs["domain"] = config.cookie_domain
    response.delete_cookie(**kwargs)  # type: ignore[arg-type]
