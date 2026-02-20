from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import AevoApiError
from ..utils import err_response, ok_response


def _pick(d: dict, keys: list[str]) -> dict:
    """Whitelist fields from a dict to reduce response size."""
    return {k: d[k] for k in keys if k in d}


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


def _slim_markets(raw: list) -> list:
    return [_pick(m, MARKET_FIELDS) for m in raw]


def _slim_orderbook(raw: dict) -> dict:
    bids = raw.get("bids", [])[:ORDERBOOK_DEPTH]
    asks = raw.get("asks", [])[:ORDERBOOK_DEPTH]
    # Keep only [price, amount] per level (drop IV and other fields)
    result: dict[str, Any] = {
        "bids": [[lv[0], lv[1]] if isinstance(lv, list) and len(lv) >= 2 else lv for lv in bids],
        "asks": [[lv[0], lv[1]] if isinstance(lv, list) and len(lv) >= 2 else lv for lv in asks],
    }
    # Preserve instrument_name/timestamp if present
    for key in ("instrument_name", "timestamp"):
        if key in raw:
            result[key] = raw[key]
    return result


def _slim_trades(raw: list) -> list:
    return [_pick(t, TRADE_FIELDS) for t in raw]


def register_market_tools(mcp: FastMCP, client: Any) -> dict[str, Any]:
    @mcp.tool()
    def assets() -> dict[str, Any]:
        """List supported AEVO assets."""
        try:
            return ok_response(client.get_assets())
        except AevoApiError as exc:
            return err_response("failed to fetch assets", str(exc))
        except Exception as exc:
            return err_response("failed to fetch assets", str(exc))

    @mcp.tool()
    def markets(asset: str = "", instrument_type: str = "") -> dict[str, Any]:
        """List markets, optionally filtered by asset and instrument_type. Returns slim fields: instrument_name, type, asset, mark_price, is_active, and option fields (strike, option_type, expiry)."""
        try:
            raw = client.get_markets(asset=asset, instrument_type=instrument_type)
            return ok_response(_slim_markets(raw))
        except AevoApiError as exc:
            return err_response("failed to fetch markets", str(exc))
        except Exception as exc:
            return err_response("failed to fetch markets", str(exc))

    @mcp.tool()
    def orderbook(instrument_name: str) -> dict[str, Any]:
        """Return top 10 bids and asks for a given instrument. Each level: [price, amount]."""
        if not instrument_name:
            return err_response("instrument_name is required")
        try:
            raw = client.get_orderbook(instrument_name)
            return ok_response(_slim_orderbook(raw))
        except AevoApiError as exc:
            return err_response("failed to fetch orderbook", str(exc))
        except Exception as exc:
            return err_response("failed to fetch orderbook", str(exc))

    @mcp.tool()
    def instrument(instrument_name: str) -> dict[str, Any]:
        """Return full instrument metadata by name or id."""
        if not instrument_name:
            return err_response("instrument_name is required")
        try:
            return ok_response(client.get_instrument(instrument_name))
        except AevoApiError as exc:
            return err_response("failed to fetch instrument", str(exc))
        except Exception as exc:
            return err_response("failed to fetch instrument", str(exc))

    @mcp.tool()
    def funding_rate(instrument_name: str) -> dict[str, Any]:
        """Return current funding rate for a perpetual instrument."""
        if not instrument_name:
            return err_response("instrument_name is required")
        try:
            return ok_response(client.get_funding(instrument_name))
        except AevoApiError as exc:
            return err_response("failed to fetch funding rate", str(exc))
        except Exception as exc:
            return err_response("failed to fetch funding rate", str(exc))

    @mcp.tool()
    def funding_history(
        instrument_name: str,
        start_time: str = "",
        end_time: str = "",
        limit: str = "50",
        offset: str = "",
    ) -> dict[str, Any]:
        """Return historical funding rates for a perpetual instrument (default limit: 50)."""
        if not instrument_name:
            return err_response("instrument_name is required")
        try:
            return ok_response(client.get_funding_history(instrument_name, start_time, end_time, limit, offset))
        except AevoApiError as exc:
            return err_response("failed to fetch funding history", str(exc))
        except Exception as exc:
            return err_response("failed to fetch funding history", str(exc))

    @mcp.tool()
    def trade_history(instrument_name: str) -> dict[str, Any]:
        """Return recent public trades for an instrument. Each trade: price, amount, side, created_at."""
        if not instrument_name:
            return err_response("instrument_name is required")
        try:
            raw = client.get_trade_history_public(instrument_name)
            return ok_response(_slim_trades(raw) if isinstance(raw, list) else raw)
        except AevoApiError as exc:
            return err_response("failed to fetch trade history", str(exc))
        except Exception as exc:
            return err_response("failed to fetch trade history", str(exc))

    @mcp.tool()
    def statistics() -> dict[str, Any]:
        """Return exchange-wide market statistics (volume, open interest, etc)."""
        try:
            return ok_response(client.get_statistics())
        except AevoApiError as exc:
            return err_response("failed to fetch statistics", str(exc))
        except Exception as exc:
            return err_response("failed to fetch statistics", str(exc))

    @mcp.tool()
    def index_price(asset: str) -> dict[str, Any]:
        """Return the index (spot reference) price for an asset."""
        if not asset:
            return err_response("asset is required")
        try:
            return ok_response(client.get_index(asset))
        except AevoApiError as exc:
            return err_response("failed to fetch index price", str(exc))
        except Exception as exc:
            return err_response("failed to fetch index price", str(exc))

    @mcp.tool()
    def index_history(
        asset: str,
        resolution: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: str = "50",
    ) -> dict[str, Any]:
        """Return historical index prices for an asset (default limit: 50)."""
        if not asset:
            return err_response("asset is required")
        try:
            return ok_response(client.get_index_history(asset, resolution, start_time, end_time, limit))
        except AevoApiError as exc:
            return err_response("failed to fetch index history", str(exc))
        except Exception as exc:
            return err_response("failed to fetch index history", str(exc))

    @mcp.tool()
    def mark_history(
        instrument_name: str,
        resolution: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: str = "50",
    ) -> dict[str, Any]:
        """Return historical mark prices for an instrument (default limit: 50)."""
        if not instrument_name:
            return err_response("instrument_name is required")
        try:
            return ok_response(client.get_mark_history(instrument_name, resolution, start_time, end_time, limit))
        except AevoApiError as exc:
            return err_response("failed to fetch mark history", str(exc))
        except Exception as exc:
            return err_response("failed to fetch mark history", str(exc))

    @mcp.tool()
    def settlement_history(
        asset: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: str = "50",
    ) -> dict[str, Any]:
        """Return settlement history, optionally filtered by asset (default limit: 50)."""
        try:
            return ok_response(client.get_settlement_history(asset, start_time, end_time, limit))
        except AevoApiError as exc:
            return err_response("failed to fetch settlement history", str(exc))
        except Exception as exc:
            return err_response("failed to fetch settlement history", str(exc))

    @mcp.tool()
    def expiries(asset: str) -> dict[str, Any]:
        """Return available expiry dates for an asset's options/futures."""
        if not asset:
            return err_response("asset is required")
        try:
            return ok_response(client.get_expiries(asset))
        except AevoApiError as exc:
            return err_response("failed to fetch expiries", str(exc))
        except Exception as exc:
            return err_response("failed to fetch expiries", str(exc))

    @mcp.tool()
    def server_time() -> dict[str, Any]:
        """Return the AEVO exchange server time."""
        try:
            return ok_response(client.get_time())
        except AevoApiError as exc:
            return err_response("failed to fetch server time", str(exc))
        except Exception as exc:
            return err_response("failed to fetch server time", str(exc))

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
