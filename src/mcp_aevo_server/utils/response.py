from __future__ import annotations

from typing import Any, Dict, Optional


def ok_response(payload: Any) -> Dict[str, Any]:
    return {"ok": True, "result": payload}


def err_response(message: str, details: Optional[str] = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {"ok": False, "error": message}
    if details:
        body["details"] = details
    return body
