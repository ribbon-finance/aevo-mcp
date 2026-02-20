from __future__ import annotations

from types import SimpleNamespace

from mcp.server.fastmcp import FastMCP

from mcp_aevo_server.tools.register import register_registration_tools


class FakeClient:
    def __init__(self):
        self.register_calls = []
        self._api_key = ""
        self._api_secret = ""

    def register(self, payload):
        self.register_calls.append(payload)
        return {"api_key": "k", "api_secret": "s", "success": True}

    def set_credentials(self, api_key: str, api_secret: str):
        self._api_key = api_key
        self._api_secret = api_secret


def test_register_tool_returns_credentials_and_stores():
    client = FakeClient()
    config = SimpleNamespace(
        account_private_key="0x" + "1" * 64,
        signing_key_private_key="0x" + "2" * 64,
        account_address="",
        signing_key_address="",
        network=SimpleNamespace(name="Aevo Mainnet", chain_id=1),
    )

    mcp = FastMCP("AEVO")
    tools = register_registration_tools(mcp, client, config)

    response = tools["register_account"]()
    assert response["ok"] is True
    data = response["result"]
    assert data["stored"] is True
    assert data["api_key"] == "k"
    assert data["api_secret"] == "s"
    assert client._api_key == "k"
    assert client._api_secret == "s"
    assert client.register_calls
