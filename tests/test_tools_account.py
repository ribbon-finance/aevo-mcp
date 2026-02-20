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

    def get_account_trade_history(self, **kwargs):
        self.calls.append(("account_trade_history", kwargs))
        return [{"trade_id": "t1", "price": "50000"}]

    def get_order_history(self, **kwargs):
        self.calls.append(("order_history", kwargs))
        return [{"order_id": "o1", "status": "filled"}]


def _make_config(**overrides):
    defaults = dict(
        wallet_address="0x1111111111111111111111111111111111111111",
        wallet_private_key="",
        signing_key_private_key="",
        environment="mainnet",
        api_base_url="https://api.aevo.xyz",
        mcp_host="127.0.0.1",
        mcp_port=8080,
        mcp_path="/mcp",
        mcp_transport="streamable-http",
        has_credentials=False,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_account_tool_requires_credentials_for_sensitive_calls():
    client = FakeClient()
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    assert tools["status"]()["result"]["has_api_credentials"] is False

    account = tools["account"]()
    assert account["ok"] is False
    assert "missing AEVO_API_KEY/AEVO_API_SECRET" in account.get("details", "")


def test_account_tool_without_auth_returns_data_for_status_only():
    client = FakeClient()
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    status = tools["status"]()
    assert status["ok"] is True
    assert status["result"]["wallet_address"] == "0x1111111111111111111111111111111111111111"


def test_account_trade_history_requires_credentials():
    client = FakeClient()
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    result = tools["account_trade_history"]()
    assert result["ok"] is False
    assert "missing AEVO_API_KEY/AEVO_API_SECRET" in result.get("details", "")


def test_account_trade_history_returns_data():
    client = FakeClient()
    client.has_credentials = True
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    result = tools["account_trade_history"]()
    assert result["ok"] is True
    assert result["result"][0]["trade_id"] == "t1"


def test_order_history_requires_credentials():
    client = FakeClient()
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    result = tools["order_history"]()
    assert result["ok"] is False
    assert "missing AEVO_API_KEY/AEVO_API_SECRET" in result.get("details", "")


def test_order_history_returns_data():
    client = FakeClient()
    client.has_credentials = True
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    result = tools["order_history"]()
    assert result["ok"] is True
    assert result["result"][0]["order_id"] == "o1"
