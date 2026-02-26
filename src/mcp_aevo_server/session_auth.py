from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import Context


@dataclass(frozen=True)
class SessionCredentials:
    api_key: str = ""
    api_secret: str = ""
    wallet_address: str = ""
    wallet_private_key: str = ""
    signing_key_private_key: str = ""
    updated_at: float = 0.0

    def merged(self, **overrides: Any) -> SessionCredentials:
        data = {
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "wallet_address": self.wallet_address,
            "wallet_private_key": self.wallet_private_key,
            "signing_key_private_key": self.signing_key_private_key,
            "updated_at": time.time(),
        }
        for key, value in overrides.items():
            if isinstance(value, str):
                normalized = value.strip()
                if normalized:
                    data[key] = normalized
            elif value is not None:
                data[key] = value
        return SessionCredentials(**data)

    @property
    def has_api_credentials(self) -> bool:
        return bool(self.api_key and self.api_secret)

    @property
    def has_signing_credentials(self) -> bool:
        return bool((self.wallet_address or self.wallet_private_key) and self.signing_key_private_key)


class SessionAuthStore:
    def __init__(self, ttl_seconds: int = 12 * 60 * 60):
        self._ttl_seconds = max(0, int(ttl_seconds))
        self._lock = threading.RLock()
        self._store: dict[str, SessionCredentials] = {}

    @staticmethod
    def session_key_from_context(ctx: Context | Any | None) -> str | None:
        if ctx is None:
            return None
        request_context = getattr(ctx, "request_context", None)
        if request_context is not None:
            session = getattr(request_context, "session", None)
            if session is not None:
                session_id = getattr(session, "session_id", None) or getattr(session, "id", None)
                if session_id:
                    return f"session:{session_id}"
                return f"session_obj:{id(session)}"

        client_id = getattr(ctx, "client_id", None)
        if client_id:
            return f"client:{client_id}"
        return None

    def _prune_locked(self, now: float) -> None:
        if self._ttl_seconds <= 0:
            return
        stale = [
            key for key, creds in self._store.items() if creds.updated_at and now - creds.updated_at > self._ttl_seconds
        ]
        for key in stale:
            self._store.pop(key, None)

    def get(self, key: str) -> SessionCredentials | None:
        with self._lock:
            now = time.time()
            self._prune_locked(now)
            return self._store.get(key)

    def get_for_context(self, ctx: Context | Any | None) -> SessionCredentials | None:
        key = self.session_key_from_context(ctx)
        if not key:
            return None
        return self.get(key)

    def upsert(self, key: str, **fields: Any) -> SessionCredentials:
        with self._lock:
            current = self._store.get(key, SessionCredentials())
            merged = current.merged(**fields)
            self._store[key] = merged
            return merged

    def upsert_for_context(self, ctx: Context | Any | None, **fields: Any) -> SessionCredentials | None:
        key = self.session_key_from_context(ctx)
        if not key:
            return None
        return self.upsert(key, **fields)

    def clear(self, key: str) -> bool:
        with self._lock:
            return self._store.pop(key, None) is not None

    def clear_for_context(self, ctx: Context | Any | None) -> bool:
        key = self.session_key_from_context(ctx)
        if not key:
            return False
        return self.clear(key)
