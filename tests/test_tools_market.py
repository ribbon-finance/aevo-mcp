from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from mcp_aevo_server.tools.market import register_market_tools


class FakeClient:
    def __init__(self):
        self.calls = []

    def get_assets(self):
        self.calls.append("assets")
        return ["USDC", "BTC"]

    def get_markets(self, asset: str = "", instrument_type: str = ""):
        self.calls.append(("markets", asset, instrument_type))
        return [{"instrument_name": "BTC-USDC"}]

    def get_orderbook(self, instrument_name: str):
        self.calls.append(("orderbook", instrument_name))
        return {"bids": [], "asks": []}

    def get_instrument(self, instrument_name: str):
        self.calls.append(("instrument", instrument_name))
        return {"instrument_name": instrument_name}


def test_market_tools_register_and_call():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    assert tools["assets"]() == {"ok": True, "result": ["USDC", "BTC"]}
    assert tools["markets"]() == {"ok": True, "result": [{"instrument_name": "BTC-USDC"}]}
    assert tools["orderbook"]("BTC-USDC") == {"ok": True, "result": {"bids": [], "asks": []}}
    assert tools["instrument"]("BTC-USDC") == {"ok": True, "result": {"instrument_name": "BTC-USDC"}}
    assert tools["orderbook"]("") == {"ok": False, "error": "instrument_name is required"}


def test_market_tools_required_calls():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    register_market_tools(mcp, client)
    assert client.calls
