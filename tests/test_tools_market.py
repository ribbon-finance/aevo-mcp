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

    def get_funding(self, instrument_name: str):
        self.calls.append(("funding", instrument_name))
        return {"funding_rate": "0.0001"}

    def get_funding_history(self, instrument_name, start_time="", end_time="", limit="", offset=""):
        self.calls.append(("funding_history", instrument_name))
        return [{"funding_rate": "0.0001", "timestamp": "1000"}]

    def get_trade_history_public(self, instrument_name: str):
        self.calls.append(("trade_history_public", instrument_name))
        return [{"price": "50000", "amount": "1"}]

    def get_statistics(self):
        self.calls.append("statistics")
        return {"daily_volume": "1000000"}

    def get_index(self, asset: str):
        self.calls.append(("index", asset))
        return {"price": "50000"}

    def get_index_history(self, asset, resolution="", start_time="", end_time="", limit=""):
        self.calls.append(("index_history", asset))
        return [{"price": "50000", "timestamp": "1000"}]

    def get_mark_history(self, instrument_name, resolution="", start_time="", end_time="", limit=""):
        self.calls.append(("mark_history", instrument_name))
        return [{"mark_price": "50001", "timestamp": "1000"}]

    def get_settlement_history(self, asset="", start_time="", end_time="", limit=""):
        self.calls.append(("settlement_history", asset))
        return [{"settlement_price": "50000"}]

    def get_expiries(self, asset: str):
        self.calls.append(("expiries", asset))
        return ["2025-03-28", "2025-06-27"]

    def get_time(self):
        self.calls.append("time")
        return {"timestamp": 1700000000}


def test_market_tools_register_and_call():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    assert tools["assets"]() == {"ok": True, "result": ["USDC", "BTC"]}
    assert tools["markets"]() == {"ok": True, "result": [{"instrument_name": "BTC-USDC"}]}
    assert tools["orderbook"]("BTC-USDC") == {"ok": True, "result": {"bids": [], "asks": []}}
    assert tools["instrument"]("BTC-USDC") == {"ok": True, "result": {"instrument_name": "BTC-USDC"}}
    assert tools["orderbook"]("") == {"ok": False, "error": "instrument_name is required"}


def test_market_tools_register_all_expected_keys():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)
    expected = {
        "assets", "markets", "orderbook", "instrument",
        "funding_rate", "funding_history", "trade_history", "statistics",
        "index_price", "index_history", "mark_history", "settlement_history",
        "expiries", "server_time",
    }
    assert set(tools.keys()) == expected


def test_funding_rate():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = tools["funding_rate"]("ETH-PERP")
    assert result["ok"] is True
    assert result["result"]["funding_rate"] == "0.0001"

    assert tools["funding_rate"]("") == {"ok": False, "error": "instrument_name is required"}


def test_funding_history():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = tools["funding_history"]("ETH-PERP")
    assert result["ok"] is True
    assert len(result["result"]) == 1

    assert tools["funding_history"]("") == {"ok": False, "error": "instrument_name is required"}


def test_trade_history():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = tools["trade_history"]("ETH-PERP")
    assert result["ok"] is True
    assert result["result"][0]["price"] == "50000"

    assert tools["trade_history"]("") == {"ok": False, "error": "instrument_name is required"}


def test_statistics():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = tools["statistics"]()
    assert result["ok"] is True
    assert result["result"]["daily_volume"] == "1000000"


def test_index_price():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = tools["index_price"]("BTC")
    assert result["ok"] is True
    assert result["result"]["price"] == "50000"

    assert tools["index_price"]("") == {"ok": False, "error": "asset is required"}


def test_index_history():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = tools["index_history"]("BTC")
    assert result["ok"] is True
    assert len(result["result"]) == 1

    assert tools["index_history"]("") == {"ok": False, "error": "asset is required"}


def test_mark_history():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = tools["mark_history"]("ETH-PERP")
    assert result["ok"] is True
    assert result["result"][0]["mark_price"] == "50001"

    assert tools["mark_history"]("") == {"ok": False, "error": "instrument_name is required"}


def test_settlement_history():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = tools["settlement_history"]()
    assert result["ok"] is True
    assert len(result["result"]) == 1


def test_expiries():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = tools["expiries"]("BTC")
    assert result["ok"] is True
    assert "2025-03-28" in result["result"]

    assert tools["expiries"]("") == {"ok": False, "error": "asset is required"}


def test_server_time():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = tools["server_time"]()
    assert result["ok"] is True
    assert result["result"]["timestamp"] == 1700000000
