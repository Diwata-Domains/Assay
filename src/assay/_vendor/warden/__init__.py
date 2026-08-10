"""Warden — shared auth package for Diwata products."""

from .config import WardenConfig, WardenConfigError
from .exceptions import TokenExpired, TokenInvalid, WardenError
from .gate import GateClientConfig, GateExchangeError, begin_login_url, exchange_code
from .middleware import WardenMiddleware
from .session import clear_session_cookie, set_session_cookie
from .tokens import decode_token_unverified, issue_token, verify_token

__all__ = [
    "WardenConfig",
    "WardenConfigError",
    "WardenError",
    "TokenExpired",
    "TokenInvalid",
    "WardenMiddleware",
    "GateClientConfig",
    "GateExchangeError",
    "begin_login_url",
    "exchange_code",
    "issue_token",
    "verify_token",
    "decode_token_unverified",
    "set_session_cookie",
    "clear_session_cookie",
]
