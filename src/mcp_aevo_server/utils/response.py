from __future__ import annotations

from typing import Any


def pick(d: dict, keys: list[str]) -> dict:
    """Whitelist fields from a dict to reduce response size."""
    return {k: d[k] for k in keys if k in d}


def ok_response(payload: Any) -> dict[str, Any]:
    return {"ok": True, "result": payload}


def err_response(message: str, details: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"ok": False, "error": message}
    if details:
        body["details"] = details
    return body
