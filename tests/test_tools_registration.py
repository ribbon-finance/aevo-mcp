from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_aevo_server.session_auth import SessionAuthStore
from mcp_aevo_server.tools.register import register_registration_tools


class FakeClient:
    def __init__(self):
        self.register_calls = []
        self._api_key = ""
        self._api_secret = ""

    async def register(self, payload):
        self.register_calls.append(payload)
        return {"api_key": "k", "api_secret": "s", "success": True}

    def set_credentials(self, api_key: str, api_secret: str):
        self._api_key = api_key
        self._api_secret = api_secret


MOCK_SIGNED = {
    "account_signature": "0xdeadbeef01",
    "signing_key_signature": "0xdeadbeef02",
}


@pytest.mark.asyncio
@patch("mcp_aevo_server.tools.register.sign_register_payload", return_value=dict(MOCK_SIGNED))
async def test_register_tool_stores_credentials_by_default(mock_sign):
    client = FakeClient()
    config = SimpleNamespace(
        wallet_private_key="0x" + "1" * 64,
        signing_key_private_key="0x" + "2" * 64,
        wallet_address="",
        network=SimpleNamespace(name="Aevo Mainnet", chain_id=1),
    )

    mcp = FastMCP("AEVO")
    tools = register_registration_tools(mcp, client, config)

    response = await tools["register_account"]()
    assert response["stored"] is True
    assert response["api_key"] == "k"
    assert response["api_secret"] == "s"
    assert client._api_key == "k"
    assert client._api_secret == "s"
    assert client.register_calls


@pytest.mark.asyncio
@patch("mcp_aevo_server.tools.register.sign_register_payload", return_value=dict(MOCK_SIGNED))
async def test_register_tool_can_store_credentials_when_requested(mock_sign):
    client = FakeClient()
    config = SimpleNamespace(
        wallet_private_key="0x" + "1" * 64,
        signing_key_private_key="0x" + "2" * 64,
        wallet_address="",
        network=SimpleNamespace(name="Aevo Mainnet", chain_id=1),
    )

    mcp = FastMCP("AEVO")
    tools = register_registration_tools(mcp, client, config)

    response = await tools["register_account"](store_credentials=True)
    assert response["stored"] is True
    assert client._api_key == "k"
    assert client._api_secret == "s"
    assert client.register_calls


@pytest.mark.asyncio
@patch("mcp_aevo_server.tools.register.sign_register_payload", return_value=dict(MOCK_SIGNED))
async def test_register_tool_stores_credentials_in_session_scope_when_ctx_present(mock_sign):
    client = FakeClient()
    config = SimpleNamespace(
        wallet_private_key="0x" + "1" * 64,
        signing_key_private_key="0x" + "2" * 64,
        wallet_address="0x1111111111111111111111111111111111111111",
        network=SimpleNamespace(name="Aevo Mainnet", chain_id=1),
    )
    auth_store = SessionAuthStore()
    ctx = SimpleNamespace(client_id="user-4")

    mcp = FastMCP("AEVO")
    tools = register_registration_tools(mcp, client, config, auth_store=auth_store)

    response = await tools["register_account"](ctx=ctx)
    assert response["stored"] is True
    assert client._api_key == ""
    assert client._api_secret == ""
    session = auth_store.get_for_context(ctx)
    assert session is not None
    assert session.api_key == "k"
    assert session.api_secret == "s"
