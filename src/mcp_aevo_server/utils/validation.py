from __future__ import annotations

from typing import Any


def parse_int_field(value: str | int, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be integer-like") from exc


def resolve_auth(
    api_key: str = "",
    api_secret: str = "",
    session_api_key: str = "",
    session_api_secret: str = "",
) -> tuple[str, str] | None:
    """Resolve API credentials from explicit params or session store.

    Returns (key, secret) tuple or None if no credentials available.
    Raises RuntimeError if only one of api_key/api_secret is provided.
    """
    key = (api_key or "").strip()
    secret = (api_secret or "").strip()
    if bool(key) != bool(secret):
        raise RuntimeError("api_key and api_secret must be provided together")
    if key and secret:
        return (key, secret)
    if session_api_key and session_api_secret:
        return (session_api_key, session_api_secret)
    return None


def require_api_credentials(
    client: Any,
    api_key: str = "",
    api_secret: str = "",
    session_api_key: str = "",
    session_api_secret: str = "",
) -> tuple[str, str] | None:
    """Resolve auth and raise if no credentials are available anywhere."""
    auth = resolve_auth(
        api_key=api_key,
        api_secret=api_secret,
        session_api_key=session_api_key,
        session_api_secret=session_api_secret,
    )
    if auth is None and not client.has_credentials:
        raise RuntimeError("missing AEVO_API_KEY/AEVO_API_SECRET; provide api_key/api_secret or call register_account")
    return auth
