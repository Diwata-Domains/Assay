"""Warden configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WardenConfig:
    """Auth configuration shared across all Diwata products.

    Attributes:
        secret: HS256 signing secret — read from WARDEN_SECRET env var in practice.
        algorithm: JWT algorithm. HS256 for shared-secret, RS256 for future key-pair use.
        cookie_name: Name of the session cookie set on the browser.
        cookie_domain: Parent domain for SSO (e.g. ".diwata.domains" covers all subdomains).
        ttl_seconds: Token lifetime in seconds. Default 8 hours.
        secure_cookie: Set Secure flag on the cookie. Disable only in local dev.
        samesite: SameSite cookie policy.
    """

    secret: str
    algorithm: str = "HS256"
    cookie_name: str = "warden_session"
    cookie_domain: str = ""
    ttl_seconds: int = 28800  # 8 hours
    secure_cookie: bool = True
    samesite: str = "lax"

    @classmethod
    def from_env(cls) -> WardenConfig:
        """Load config from environment variables.

        Required env vars:
            WARDEN_SECRET — signing secret (min 32 chars recommended)

        Optional:
            WARDEN_COOKIE_NAME     (default: warden_session)
            WARDEN_COOKIE_DOMAIN   (default: "")
            WARDEN_TTL_SECONDS     (default: 28800)
            WARDEN_SECURE_COOKIE   (default: true)
        """
        import os

        secret = os.environ.get("WARDEN_SECRET", "").strip()
        if not secret:
            raise WardenConfigError("WARDEN_SECRET env var is required")

        ttl_raw = os.environ.get("WARDEN_TTL_SECONDS", "28800")
        try:
            ttl = int(ttl_raw)
        except ValueError:
            raise WardenConfigError(f"WARDEN_TTL_SECONDS must be an integer, got {ttl_raw!r}")

        secure_raw = os.environ.get("WARDEN_SECURE_COOKIE", "true").lower()
        secure = secure_raw not in ("0", "false", "no")

        return cls(
            secret=secret,
            cookie_name=os.environ.get("WARDEN_COOKIE_NAME", "warden_session"),
            cookie_domain=os.environ.get("WARDEN_COOKIE_DOMAIN", ""),
            ttl_seconds=ttl,
            secure_cookie=secure,
        )


class WardenConfigError(Exception):
    """Raised when Warden configuration is invalid."""
