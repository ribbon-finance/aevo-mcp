from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP

from mcp_aevo_server.tools.order import register_order_tools


class FakeClient:
    def __init__(self):
        self.calls = []
        self.has_credentials = True
        self.order = None

    def resolve_instrument_id(self, instrument: str):
        self.calls.append(("resolve", instrument))
        return "123" if instrument == "BTC-USDC" else ""

    def create_order(self, payload):
        self.calls.append(("create", payload))
        self.order = payload
        return {"id": "order-1", "payload": payload}

    def get_orders(self):
        return []

    def get_order(self, order_id: str):
        return {"order_id": order_id}

    def cancel_order(self, order_id: str):
        return {"status": "cancelled", "order_id": order_id}

    def cancel_orders(self, order_ids, instrument_type=None):
        return {"status": "cancelled", "order_ids": order_ids}

    def cancel_all_orders(self, asset=None, instrument_type=None):
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


@patch("mcp_aevo_server.tools.order.sign_order_payload", return_value=dict(MOCK_SIGNED_PAYLOAD))
def test_order_tool_build_and_create(mock_sign):
    client = FakeClient()
    config = _make_config()

    mcp = FastMCP("AEVO")
    tools = register_order_tools(mcp, client, config)

    payload = tools["build_order"]("BTC-USDC", True, "10", "50000")
    assert payload["ok"] is True
    assert payload["result"]["maker"]
    assert payload["result"]["instrument"] == "123"

    mock_sign.return_value = dict(MOCK_SIGNED_PAYLOAD)
    created = tools["create_order"]("BTC-USDC", True, "10", "50000")
    assert created["ok"] is True
    assert created["result"]["id"] == "order-1"


def test_order_tools_require_credentials():
    client = FakeClient()
    client.has_credentials = False
    config = _make_config()
    mcp = FastMCP("AEVO")
    tools = register_order_tools(mcp, client, config)

    response = tools["create_order"]("BTC-USDC", True, "10", "50000")
    assert response["ok"] is False
    assert "missing AEVO_API_KEY/AEVO_API_SECRET" in response.get("details", "")


@patch("mcp_aevo_server.tools.order.sign_order_payload", return_value=dict(MOCK_SIGNED_PAYLOAD))
def test_build_order_with_stop_trigger(mock_sign):
    client = FakeClient()
    config = _make_config()
    mcp = FastMCP("AEVO")
    tools = register_order_tools(mcp, client, config)

    result = tools["build_order"](
        "BTC-USDC", True, "10", "50000",
        stop="STOP_LOSS",
        trigger="49000",
        close_position=True,
        partial_position=True,
    )
    assert result["ok"] is True
    payload = result["result"]
    assert payload["stop"] == "STOP_LOSS"
    assert payload["trigger"] == "49000"
    assert payload["close_position"] is True
    assert payload["partial_position"] is True


@patch("mcp_aevo_server.tools.order.sign_order_payload", return_value=dict(MOCK_SIGNED_PAYLOAD))
def test_build_order_without_stop_trigger_omits_fields(mock_sign):
    client = FakeClient()
    config = _make_config()
    mcp = FastMCP("AEVO")
    tools = register_order_tools(mcp, client, config)

    result = tools["build_order"]("BTC-USDC", True, "10", "50000")
    assert result["ok"] is True
    payload = result["result"]
    assert "stop" not in payload
    assert "trigger" not in payload
    assert "close_position" not in payload
    assert "partial_position" not in payload
