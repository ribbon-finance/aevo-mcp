from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..utils.response import pick

MARKET_FIELDS = [
    "instrument_name",
    "instrument_type",
    "asset",
    "mark_price",
    "index_price",
    "is_active",
    "strike",
    "option_type",
    "expiry",
]

TRADE_FIELDS = ["price", "amount", "side", "created_at"]

ORDERBOOK_DEPTH = 10

_READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)


def _slim_markets(raw: list) -> list:
    return [pick(m, MARKET_FIELDS) for m in raw]


def _slim_orderbook(raw: dict) -> dict:
    bids = raw.get("bids", [])[:ORDERBOOK_DEPTH]
    asks = raw.get("asks", [])[:ORDERBOOK_DEPTH]
    result: dict[str, Any] = {
        "bids": [[lv[0], lv[1]] if isinstance(lv, list) and len(lv) >= 2 else lv for lv in bids],
        "asks": [[lv[0], lv[1]] if isinstance(lv, list) and len(lv) >= 2 else lv for lv in asks],
    }
    for key in ("instrument_name", "timestamp"):
        if key in raw:
            result[key] = raw[key]
    return result


def _slim_trades(raw: list) -> list:
    return [pick(t, TRADE_FIELDS) for t in raw]


def register_market_tools(mcp: FastMCP, client: Any) -> dict[str, Any]:
    @mcp.tool(name="aevo_list_assets", annotations=_READ_ONLY)
    async def assets() -> list:
        """List all supported assets on AEVO exchange.

        Returns a list of asset ticker symbols (e.g. ["ETH", "BTC", "USDC"]).
        """
        return await client.get_assets()

    @mcp.tool(name="aevo_list_markets", annotations=_READ_ONLY)
    async def markets(asset: str = "", instrument_type: str = "") -> list:
        """List available markets, optionally filtered by asset and instrument_type.

        Returns slim fields per market: instrument_name, type, asset, mark_price,
        is_active, and option fields (strike, option_type, expiry).

        Args:
            asset: Filter by asset symbol (e.g. "ETH", "BTC"). Empty = all assets.
            instrument_type: Filter by type (e.g. "PERPETUAL", "OPTION"). Empty = all types.
        """
        raw = await client.get_markets(asset=asset, instrument_type=instrument_type)
        return _slim_markets(raw)

    @mcp.tool(name="aevo_get_orderbook", annotations=_READ_ONLY)
    async def orderbook(instrument_name: str) -> dict:
        """Return top 10 bids and asks for a given instrument.

        Each level is [price, amount]. Useful for checking liquidity and spread.

        Args:
            instrument_name: Instrument to query (e.g. "ETH-PERP", "BTC-USDC").
        """
        raw = await client.get_orderbook(instrument_name)
        return _slim_orderbook(raw)

    @mcp.tool(name="aevo_get_instrument", annotations=_READ_ONLY)
    async def instrument(instrument_name: str) -> dict:
        """Return full instrument metadata by name or id.

        Includes tick size, min order size, margin requirements, and settlement info.

        Args:
            instrument_name: Instrument name (e.g. "ETH-PERP") or numeric instrument id.
        """
        return await client.get_instrument(instrument_name)

    @mcp.tool(name="aevo_get_funding_rate", annotations=_READ_ONLY)
    async def funding_rate(instrument_name: str) -> dict:
        """Return the current funding rate for a perpetual instrument.

        Positive rate = longs pay shorts. Negative rate = shorts pay longs.

        Args:
            instrument_name: Perpetual instrument name (e.g. "ETH-PERP").
        """
        return await client.get_funding(instrument_name)

    @mcp.tool(name="aevo_get_funding_history", annotations=_READ_ONLY)
    async def funding_history(
        instrument_name: str,
        start_time: str = "",
        end_time: str = "",
        limit: str = "50",
        offset: str = "",
    ) -> list:
        """Return historical funding rates for a perpetual instrument.

        Args:
            instrument_name: Perpetual instrument name (e.g. "ETH-PERP").
            start_time: Start timestamp (unix seconds). Empty = no lower bound.
            end_time: End timestamp (unix seconds). Empty = no upper bound.
            limit: Max records to return (default 50).
            offset: Pagination offset.
        """
        return await client.get_funding_history(instrument_name, start_time, end_time, limit, offset)

    @mcp.tool(name="aevo_get_trade_history", annotations=_READ_ONLY)
    async def trade_history(instrument_name: str) -> list:
        """Return recent public trades for an instrument.

        Each trade includes: price, amount, side, created_at.

        Args:
            instrument_name: Instrument name (e.g. "ETH-PERP").
        """
        raw = await client.get_trade_history_public(instrument_name)
        return _slim_trades(raw) if isinstance(raw, list) else raw

    @mcp.tool(name="aevo_get_statistics", annotations=_READ_ONLY)
    async def statistics() -> dict:
        """Return exchange-wide market statistics including volume and open interest."""
        return await client.get_statistics()

    @mcp.tool(name="aevo_get_index_price", annotations=_READ_ONLY)
    async def index_price(asset: str) -> dict:
        """Return the index (spot reference) price for an asset.

        Args:
            asset: Asset symbol (e.g. "ETH", "BTC").
        """
        return await client.get_index(asset)

    @mcp.tool(name="aevo_get_index_history", annotations=_READ_ONLY)
    async def index_history(
        asset: str,
        resolution: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: str = "50",
    ) -> list:
        """Return historical index prices for an asset.

        Args:
            asset: Asset symbol (e.g. "ETH", "BTC").
            resolution: Candle resolution (e.g. "1", "60", "1D"). Empty = default.
            start_time: Start timestamp (unix seconds).
            end_time: End timestamp (unix seconds).
            limit: Max records (default 50).
        """
        return await client.get_index_history(asset, resolution, start_time, end_time, limit)

    @mcp.tool(name="aevo_get_mark_history", annotations=_READ_ONLY)
    async def mark_history(
        instrument_name: str,
        resolution: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: str = "50",
    ) -> list:
        """Return historical mark prices for an instrument.

        Args:
            instrument_name: Instrument name (e.g. "ETH-PERP").
            resolution: Candle resolution. Empty = default.
            start_time: Start timestamp (unix seconds).
            end_time: End timestamp (unix seconds).
            limit: Max records (default 50).
        """
        return await client.get_mark_history(instrument_name, resolution, start_time, end_time, limit)

    @mcp.tool(name="aevo_get_settlement_history", annotations=_READ_ONLY)
    async def settlement_history(
        asset: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: str = "50",
    ) -> list:
        """Return settlement history, optionally filtered by asset.

        Args:
            asset: Filter by asset. Empty = all assets.
            start_time: Start timestamp (unix seconds).
            end_time: End timestamp (unix seconds).
            limit: Max records (default 50).
        """
        return await client.get_settlement_history(asset, start_time, end_time, limit)

    @mcp.tool(name="aevo_get_expiries", annotations=_READ_ONLY)
    async def expiries(asset: str) -> list:
        """Return available expiry dates for an asset's options/futures.

        Args:
            asset: Asset symbol (e.g. "ETH", "BTC").
        """
        return await client.get_expiries(asset)

    @mcp.tool(name="aevo_get_server_time", annotations=_READ_ONLY)
    async def server_time() -> dict:
        """Return the AEVO exchange server time."""
        return await client.get_time()

    return {
        "assets": assets,
        "markets": markets,
        "orderbook": orderbook,
        "instrument": instrument,
        "funding_rate": funding_rate,
        "funding_history": funding_history,
        "trade_history": trade_history,
        "statistics": statistics,
        "index_price": index_price,
        "index_history": index_history,
        "mark_history": mark_history,
        "settlement_history": settlement_history,
        "expiries": expiries,
        "server_time": server_time,
    }
