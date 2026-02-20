from __future__ import annotations

from types import SimpleNamespace

from mcp.server.fastmcp import FastMCP

from mcp_aevo_server.tools.account import register_account_tools


class FakeClient:
    def __init__(self):
        self.has_credentials = False
        self.calls = []

    def get_account(self):
        self.calls.append("account")
        return {"account": "0xabc"}

    def get_portfolio(self):
        self.calls.append("portfolio")
        return {"portfolio": []}

    def get_positions(self):
        self.calls.append("positions")
        return []


def test_account_tool_requires_credentials_for_sensitive_calls():
    client = FakeClient()
    config = SimpleNamespace(
        account_address="0x1111111111111111111111111111111111111111",
        account_private_key="",
        signing_key_address="0x2222222222222222222222222222222222222222",
        signing_key_private_key="",
        environment="mainnet",
        api_base_url="https://api.aevo.xyz",
        mcp_host="127.0.0.1",
        mcp_port=8080,
        mcp_path="/mcp",
        mcp_transport="streamable-http",
        has_credentials=False,
    )

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    assert tools["status"]()["result"]["has_api_credentials"] is False

    account = tools["account"]()
    assert account["ok"] is False
    assert "missing AEVO_API_KEY/AEVO_API_SECRET" in account["error"]


def test_account_tool_without_auth_returns_data_for_status_only():
    client = FakeClient()
    config = SimpleNamespace(
        account_address="0x1111111111111111111111111111111111111111",
        account_private_key="",
        signing_key_address="",
        signing_key_private_key="",
        environment="mainnet",
        api_base_url="https://api.aevo.xyz",
        mcp_host="127.0.0.1",
        mcp_port=8080,
        mcp_path="/mcp",
        mcp_transport="streamable-http",
    )

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    status = tools["status"]()
    assert status["ok"] is True
    assert status["result"]["account_address"] == "0x1111111111111111111111111111111111111111"
