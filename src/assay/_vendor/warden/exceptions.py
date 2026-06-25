"""Warden exceptions."""

from __future__ import annotations


class WardenError(Exception):
    """Base class for all Warden errors."""


class TokenInvalid(WardenError):
    """Token signature is invalid or malformed."""


class TokenExpired(WardenError):
    """Token has passed its expiry time."""
