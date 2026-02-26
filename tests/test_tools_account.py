from __future__ import annotations

from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_aevo_server.session_auth import SessionAuthStore
from mcp_aevo_server.tools.account import register_account_tools


class FakeClient:
    def __init__(self):
        self.has_credentials = False
        self.calls = []

    async def get_account(self, auth=None):
        self.calls.append(("account", auth))
        return {"account": "0xabc"}

    async def get_portfolio(self, auth=None):
        self.calls.append(("portfolio", auth))
        return {"portfolio": []}

    async def get_positions(self, auth=None):
        self.calls.append(("positions", auth))
        return []

    async def get_account_trade_history(self, auth=None, **kwargs):
        self.calls.append(("account_trade_history", auth, kwargs))
        return [{"trade_id": "t1", "price": "50000"}]

    async def get_order_history(self, auth=None, **kwargs):
        self.calls.append(("order_history", auth, kwargs))
        return [{"order_id": "o1", "status": "filled"}]

    async def resolve_instrument_id(self, instrument_name):
        return "3657" if instrument_name == "ETH-PERP" else None

    async def update_leverage(self, instrument_id, leverage, auth=None):
        self.calls.append(("update_leverage", instrument_id, leverage, auth))
        return {"instrument": instrument_id, "leverage": leverage}


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


@pytest.mark.asyncio
async def test_account_tool_requires_credentials_for_sensitive_calls():
    client = FakeClient()
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    status_result = await tools["status"]()
    assert status_result["has_api_credentials"] is False

    with pytest.raises(RuntimeError, match="missing AEVO_API_KEY/AEVO_API_SECRET"):
        await tools["account"]()


@pytest.mark.asyncio
async def test_account_tool_without_auth_returns_data_for_status_only():
    client = FakeClient()
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    status = await tools["status"]()
    assert status["wallet_address"] == "0x1111111111111111111111111111111111111111"


@pytest.mark.asyncio
async def test_account_trade_history_requires_credentials():
    client = FakeClient()
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    with pytest.raises(RuntimeError, match="missing AEVO_API_KEY/AEVO_API_SECRET"):
        await tools["account_trade_history"]()


@pytest.mark.asyncio
async def test_account_trade_history_returns_data():
    client = FakeClient()
    client.has_credentials = True
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    result = await tools["account_trade_history"]()
    assert result[0]["trade_id"] == "t1"


@pytest.mark.asyncio
async def test_order_history_requires_credentials():
    client = FakeClient()
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    with pytest.raises(RuntimeError, match="missing AEVO_API_KEY/AEVO_API_SECRET"):
        await tools["order_history"]()


@pytest.mark.asyncio
async def test_order_history_returns_data():
    client = FakeClient()
    client.has_credentials = True
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    result = await tools["order_history"]()
    assert result[0]["order_id"] == "o1"


@pytest.mark.asyncio
async def test_account_tool_accepts_runtime_credentials():
    client = FakeClient()
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    result = await tools["account"](api_key="user-key", api_secret="user-secret")
    assert result == {"account": "0xabc"}
    assert client.calls[-1] == ("account", ("user-key", "user-secret"))


@pytest.mark.asyncio
async def test_account_tool_rejects_partial_runtime_credentials():
    client = FakeClient()
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    with pytest.raises(RuntimeError, match="must be provided together"):
        await tools["account"](api_key="user-key")


@pytest.mark.asyncio
async def test_authenticate_stores_session_credentials_for_current_client():
    client = FakeClient()
    config = _make_config()
    auth_store = SessionAuthStore()
    ctx = SimpleNamespace(client_id="user-1")

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config, auth_store=auth_store)

    auth_result = await tools["authenticate"](
        api_key="user-key",
        api_secret="user-secret",
        wallet_address="0x1111111111111111111111111111111111111111",
        signing_key_private_key="0x" + "2" * 64,
        ctx=ctx,
    )
    assert auth_result["session_authenticated"] is True
    assert auth_result["can_trade"] is True
    assert "missing_for_trading" not in auth_result

    account_result = await tools["account"](ctx=ctx)
    assert account_result == {"account": "0xabc"}
    assert client.calls[-1] == ("account", ("user-key", "user-secret"))


@pytest.mark.asyncio
async def test_authenticate_api_only_shows_missing_for_trading():
    client = FakeClient()
    config = _make_config()
    auth_store = SessionAuthStore()
    ctx = SimpleNamespace(client_id="user-partial")

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config, auth_store=auth_store)

    auth_result = await tools["authenticate"](
        api_key="user-key",
        api_secret="user-secret",
        ctx=ctx,
    )
    assert auth_result["session_authenticated"] is True
    assert auth_result["can_trade"] is False
    assert "wallet_address" in auth_result["missing_for_trading"][0]
    assert "signing_key_private_key" in auth_result["missing_for_trading"][1]
    assert "aevo_authenticate" in auth_result["hint"]


@pytest.mark.asyncio
async def test_clear_auth_removes_session_credentials():
    client = FakeClient()
    config = _make_config()
    auth_store = SessionAuthStore()
    ctx = SimpleNamespace(client_id="user-2")

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config, auth_store=auth_store)

    await tools["authenticate"](api_key="user-key", api_secret="user-secret", ctx=ctx)
    clear_result = await tools["clear_auth"](ctx=ctx)
    assert clear_result["cleared"] is True

    with pytest.raises(RuntimeError, match="missing AEVO_API_KEY/AEVO_API_SECRET"):
        await tools["account"](ctx=ctx)


@pytest.mark.asyncio
async def test_onboard_unauthenticated_returns_credentials_needed():
    client = FakeClient()
    config = _make_config()
    auth_store = SessionAuthStore()
    ctx = SimpleNamespace(client_id="onboard-new")

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config, auth_store=auth_store)

    result = await tools["onboard"](ctx=ctx)
    assert result["status"] == "unauthenticated"
    assert result["can_read_account"] is False
    assert result["can_trade"] is False
    assert "credentials_url" in result
    assert "https://app.aevo.xyz/settings" in result["credentials_url"]
    assert "api_key" in result["credentials_needed"]["required_for_account_access"]


@pytest.mark.asyncio
async def test_onboard_partial_api_only():
    client = FakeClient()
    config = _make_config()
    auth_store = SessionAuthStore()
    ctx = SimpleNamespace(client_id="onboard-partial")

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config, auth_store=auth_store)

    await tools["authenticate"](api_key="k", api_secret="s", ctx=ctx)

    result = await tools["onboard"](ctx=ctx)
    assert result["status"] == "partial"
    assert result["can_read_account"] is True
    assert result["can_trade"] is False
    assert "signing_key_private_key" in result["missing_for_trading"]


@pytest.mark.asyncio
async def test_onboard_fully_authenticated_returns_ready():
    client = FakeClient()
    config = _make_config()
    auth_store = SessionAuthStore()
    ctx = SimpleNamespace(client_id="onboard-full")

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config, auth_store=auth_store)

    await tools["authenticate"](
        api_key="k",
        api_secret="s",
        wallet_address="0x1111111111111111111111111111111111111111",
        signing_key_private_key="0x" + "2" * 64,
        ctx=ctx,
    )

    result = await tools["onboard"](ctx=ctx)
    assert result["status"] == "ready"
    assert result["can_trade"] is True
    assert result["wallet_address"] == "0x1111111111111111111111111111111111111111"
    assert "Proceed" in result["actions"][0]


@pytest.mark.asyncio
async def test_onboard_ready_from_env_credentials():
    client = FakeClient()
    client.has_credentials = True
    config = _make_config(
        wallet_address="0xABCD",
        wallet_private_key="0x" + "1" * 64,
        signing_key_private_key="0x" + "2" * 64,
    )

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    result = await tools["onboard"]()
    assert result["status"] == "ready"
    assert result["can_trade"] is True
    assert result["credential_source"] == "environment"


@pytest.mark.asyncio
async def test_update_leverage():
    client = FakeClient()
    client.has_credentials = True
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    result = await tools["update_leverage"](instrument_name="ETH-PERP", leverage=5)
    assert result["instrument"] == 3657
    assert result["leverage"] == 5
    assert client.calls[-1] == ("update_leverage", 3657, 5, None)


@pytest.mark.asyncio
async def test_update_leverage_unknown_instrument():
    client = FakeClient()
    client.has_credentials = True
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_account_tools(mcp, client, config)

    with pytest.raises(RuntimeError, match="instrument not found"):
        await tools["update_leverage"](instrument_name="FAKE-PERP", leverage=10)
