from __future__ import annotations

from typing import Any


def ok_response(payload: Any) -> dict[str, Any]:
    return {"ok": True, "result": payload}


def err_response(message: str, details: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"ok": False, "error": message}
    if details:
        body["details"] = details
    return body
