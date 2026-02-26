from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_aevo_server.session_auth import SessionAuthStore
from mcp_aevo_server.tools.account import register_account_tools
from mcp_aevo_server.tools.order import register_order_tools


class FakeClient:
    def __init__(self):
        self.calls = []
        self.has_credentials = True
        self.order = None

    async def resolve_instrument_id(self, instrument: str):
        self.calls.append(("resolve", instrument))
        return "123" if instrument == "BTC-USDC" else ""

    async def create_order(self, payload, auth=None):
        self.calls.append(("create", payload, auth))
        self.order = payload
        return {"id": "order-1", "payload": payload}

    async def get_orders(self, auth=None):
        return []

    async def get_order(self, order_id: str, auth=None):
        return {"order_id": order_id}

    async def cancel_order(self, order_id: str, auth=None):
        return {"status": "cancelled", "order_id": order_id}

    async def cancel_orders(self, order_ids, instrument_type=None, auth=None):
        return {"status": "cancelled", "order_ids": order_ids}

    async def cancel_all_orders(self, asset=None, instrument_type=None, auth=None):
        return {"status": "cancelled", "asset": asset, "instrument_type": instrument_type}


def _make_config(**overrides):
    defaults = dict(
        wallet_address="0x1111111111111111111111111111111111111111",
        wallet_private_key="0x" + "1" * 64,
        signing_key_private_key="0x" + "2" * 64,
        network=SimpleNamespace(name="Aevo Mainnet", chain_id=1),
        has_credentials=True,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


MOCK_SIGNED_PAYLOAD = {
    "maker": "0x1111111111111111111111111111111111111111",
    "is_buy": True,
    "limit_price": "50000",
    "amount": "10",
    "instrument": "123",
    "salt": "999",
    "timestamp": "1700000000",
    "signature": "0xdeadbeef",
}


@pytest.mark.asyncio
@patch("mcp_aevo_server.tools.order.sign_order_payload", return_value=dict(MOCK_SIGNED_PAYLOAD))
async def test_order_tool_build_and_create(mock_sign):
    client = FakeClient()
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_order_tools(mcp, client, config)

    payload = await tools["build_order"]("BTC-USDC", True, "10", "50000")
    assert payload["maker"]
    assert payload["instrument"] == "123"

    mock_sign.return_value = dict(MOCK_SIGNED_PAYLOAD)
    created = await tools["create_order"]("BTC-USDC", True, "10", "50000")
    assert created["id"] == "order-1"


@pytest.mark.asyncio
async def test_order_tools_require_credentials():
    client = FakeClient()
    client.has_credentials = False
    config = _make_config()
    mcp = FastMCP("AEVO")
    tools = register_order_tools(mcp, client, config)

    with pytest.raises(RuntimeError, match="missing AEVO_API_KEY/AEVO_API_SECRET"):
        await tools["create_order"]("BTC-USDC", True, "10", "50000")


@pytest.mark.asyncio
@patch("mcp_aevo_server.tools.order.sign_order_payload", return_value=dict(MOCK_SIGNED_PAYLOAD))
async def test_build_order_with_stop_trigger(mock_sign):
    client = FakeClient()
    config = _make_config()
    mcp = FastMCP("AEVO")
    tools = register_order_tools(mcp, client, config)

    result = await tools["build_order"](
        "BTC-USDC",
        True,
        "10",
        "50000",
        stop="STOP_LOSS",
        trigger="49000",
        close_position=True,
        partial_position=True,
    )
    assert result["stop"] == "STOP_LOSS"
    assert result["trigger"] == "49000"
    assert result["close_position"] is True
    assert result["partial_position"] is True


@pytest.mark.asyncio
@patch("mcp_aevo_server.tools.order.sign_order_payload", return_value=dict(MOCK_SIGNED_PAYLOAD))
async def test_build_order_without_stop_trigger_omits_fields(mock_sign):
    client = FakeClient()
    config = _make_config()
    mcp = FastMCP("AEVO")
    tools = register_order_tools(mcp, client, config)

    result = await tools["build_order"]("BTC-USDC", True, "10", "50000")
    assert "stop" not in result
    assert "trigger" not in result
    assert "close_position" not in result
    assert "partial_position" not in result


@pytest.mark.asyncio
async def test_create_order_rejects_partial_runtime_api_credentials():
    client = FakeClient()
    client.has_credentials = False
    config = _make_config()
    mcp = FastMCP("AEVO")
    tools = register_order_tools(mcp, client, config)

    with pytest.raises(RuntimeError, match="must be provided together"):
        await tools["create_order"](
            "BTC-USDC",
            True,
            "10",
            "50000",
            api_key="user-key",
        )


@pytest.mark.asyncio
@patch("mcp_aevo_server.tools.order.sign_order_payload", return_value=dict(MOCK_SIGNED_PAYLOAD))
async def test_create_order_uses_session_scoped_credentials(mock_sign):
    client = FakeClient()
    client.has_credentials = False
    config = _make_config(
        wallet_address="",
        wallet_private_key="",
        signing_key_private_key="",
        has_credentials=False,
    )
    auth_store = SessionAuthStore()
    ctx = SimpleNamespace(client_id="user-3")

    mcp = FastMCP("AEVO")
    account_tools = register_account_tools(mcp, client, config, auth_store=auth_store)
    order_tools = register_order_tools(mcp, client, config, auth_store=auth_store)

    await account_tools["authenticate"](
        api_key="user-key",
        api_secret="user-secret",
        wallet_address="0x1111111111111111111111111111111111111111",
        signing_key_private_key="0x" + "2" * 64,
        ctx=ctx,
    )
    result = await order_tools["create_order"]("BTC-USDC", True, "10", "50000", ctx=ctx)
    assert result["id"] == "order-1"
    assert client.calls[-1][2] == ("user-key", "user-secret")
    assert mock_sign.call_args.kwargs["signing_key_private_key"] == "0x" + "2" * 64
