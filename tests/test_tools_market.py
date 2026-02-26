from __future__ import annotations

import pytest
from mcp.server.fastmcp import FastMCP

from mcp_aevo_server.tools.market import register_market_tools


class FakeClient:
    def __init__(self):
        self.calls = []

    async def get_assets(self):
        self.calls.append("assets")
        return ["USDC", "BTC"]

    async def get_markets(self, asset: str = "", instrument_type: str = ""):
        self.calls.append(("markets", asset, instrument_type))
        return [{"instrument_name": "BTC-USDC"}]

    async def get_orderbook(self, instrument_name: str):
        self.calls.append(("orderbook", instrument_name))
        return {"bids": [], "asks": []}

    async def get_instrument(self, instrument_name: str):
        self.calls.append(("instrument", instrument_name))
        return {"instrument_name": instrument_name}

    async def get_funding(self, instrument_name: str):
        self.calls.append(("funding", instrument_name))
        return {"funding_rate": "0.0001"}

    async def get_funding_history(self, instrument_name, start_time="", end_time="", limit="", offset=""):
        self.calls.append(("funding_history", instrument_name))
        return [{"funding_rate": "0.0001", "timestamp": "1000"}]

    async def get_trade_history_public(self, instrument_name: str):
        self.calls.append(("trade_history_public", instrument_name))
        return [{"price": "50000", "amount": "1"}]

    async def get_statistics(self):
        self.calls.append("statistics")
        return {"daily_volume": "1000000"}

    async def get_index(self, asset: str):
        self.calls.append(("index", asset))
        return {"price": "50000"}

    async def get_index_history(self, asset, resolution="", start_time="", end_time="", limit=""):
        self.calls.append(("index_history", asset))
        return [{"price": "50000", "timestamp": "1000"}]

    async def get_mark_history(self, instrument_name, resolution="", start_time="", end_time="", limit=""):
        self.calls.append(("mark_history", instrument_name))
        return [{"mark_price": "50001", "timestamp": "1000"}]

    async def get_settlement_history(self, asset="", start_time="", end_time="", limit=""):
        self.calls.append(("settlement_history", asset))
        return [{"settlement_price": "50000"}]

    async def get_expiries(self, asset: str):
        self.calls.append(("expiries", asset))
        return ["2025-03-28", "2025-06-27"]

    async def get_time(self):
        self.calls.append("time")
        return {"timestamp": 1700000000}


@pytest.mark.asyncio
async def test_market_tools_register_and_call():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    assert await tools["assets"]() == ["USDC", "BTC"]
    assert await tools["markets"]() == [{"instrument_name": "BTC-USDC"}]
    assert await tools["orderbook"]("BTC-USDC") == {"bids": [], "asks": []}
    assert await tools["instrument"]("BTC-USDC") == {"instrument_name": "BTC-USDC"}


@pytest.mark.asyncio
async def test_market_tools_register_all_expected_keys():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)
    expected = {
        "assets",
        "markets",
        "orderbook",
        "instrument",
        "funding_rate",
        "funding_history",
        "trade_history",
        "statistics",
        "index_price",
        "index_history",
        "mark_history",
        "settlement_history",
        "expiries",
        "server_time",
    }
    assert set(tools.keys()) == expected


@pytest.mark.asyncio
async def test_funding_rate():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = await tools["funding_rate"]("ETH-PERP")
    assert result["funding_rate"] == "0.0001"


@pytest.mark.asyncio
async def test_funding_history():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = await tools["funding_history"]("ETH-PERP")
    assert len(result) == 1


@pytest.mark.asyncio
async def test_trade_history():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = await tools["trade_history"]("ETH-PERP")
    assert result[0]["price"] == "50000"


@pytest.mark.asyncio
async def test_statistics():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = await tools["statistics"]()
    assert result["daily_volume"] == "1000000"


@pytest.mark.asyncio
async def test_index_price():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = await tools["index_price"]("BTC")
    assert result["price"] == "50000"


@pytest.mark.asyncio
async def test_index_history():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = await tools["index_history"]("BTC")
    assert len(result) == 1


@pytest.mark.asyncio
async def test_mark_history():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = await tools["mark_history"]("ETH-PERP")
    assert result[0]["mark_price"] == "50001"


@pytest.mark.asyncio
async def test_settlement_history():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = await tools["settlement_history"]()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_expiries():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = await tools["expiries"]("BTC")
    assert "2025-03-28" in result


@pytest.mark.asyncio
async def test_server_time():
    client = FakeClient()
    mcp = FastMCP("AEVO")
    tools = register_market_tools(mcp, client)

    result = await tools["server_time"]()
    assert result["timestamp"] == 1700000000
