from __future__ import annotations

from types import SimpleNamespace

from mcp_aevo_server.session_auth import SessionAuthStore


def _ctx(client_id: str = "", session_id: str | None = None):
    session = SimpleNamespace(session_id=session_id)
    request_context = SimpleNamespace(session=session)
    return SimpleNamespace(client_id=client_id, request_context=request_context)


def test_session_key_prefers_session_id_over_client_id():
    store = SessionAuthStore()
    ctx_a = _ctx(client_id="shared-client-id", session_id="session-a")
    ctx_b = _ctx(client_id="shared-client-id", session_id="session-b")

    store.upsert_for_context(ctx_a, api_key="k1", api_secret="s1")
    creds_b = store.get_for_context(ctx_b)

    assert creds_b is None


def test_session_key_falls_back_to_client_id_when_session_id_missing():
    store = SessionAuthStore()
    ctx = _ctx(client_id="fallback-client", session_id=None)

    store.upsert_for_context(ctx, api_key="k1", api_secret="s1")
    creds = store.get_for_context(ctx)

    assert creds is not None
    assert creds.api_key == "k1"
    assert creds.api_secret == "s1"
