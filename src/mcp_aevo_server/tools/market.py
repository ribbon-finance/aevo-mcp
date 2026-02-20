from __future__ import annotations

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from ..client import AevoApiError
from ..utils import err_response, ok_response


def register_market_tools(mcp: FastMCP, client: Any) -> Dict[str, Any]:
    @mcp.tool()
    def assets() -> Dict[str, Any]:
        """List supported AEVO assets."""
        try:
            return ok_response(client.get_assets())
        except AevoApiError as exc:
            return err_response("failed to fetch assets", str(exc))
        except Exception as exc:
            return err_response("failed to fetch assets", str(exc))

    @mcp.tool()
    def markets(asset: str = "", instrument_type: str = "") -> Dict[str, Any]:
        """List markets, optionally filtered by asset and instrument_type."""
        try:
            return ok_response(client.get_markets(asset=asset, instrument_type=instrument_type))
        except AevoApiError as exc:
            return err_response("failed to fetch markets", str(exc))
        except Exception as exc:
            return err_response("failed to fetch markets", str(exc))

    @mcp.tool()
    def orderbook(instrument_name: str) -> Dict[str, Any]:
        """Return orderbook for a given instrument name."""
        if not instrument_name:
            return err_response("instrument_name is required")
        try:
            return ok_response(client.get_orderbook(instrument_name))
        except AevoApiError as exc:
            return err_response("failed to fetch orderbook", str(exc))
        except Exception as exc:
            return err_response("failed to fetch orderbook", str(exc))

    @mcp.tool()
    def instrument(instrument_name: str) -> Dict[str, Any]:
        """Return instrument metadata by name or id."""
        if not instrument_name:
            return err_response("instrument_name is required")
        try:
            return ok_response(client.get_instrument(instrument_name))
        except AevoApiError as exc:
            return err_response("failed to fetch instrument", str(exc))
        except Exception as exc:
            return err_response("failed to fetch instrument", str(exc))

    @mcp.tool()
    def funding_rate(instrument_name: str) -> Dict[str, Any]:
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
        limit: str = "",
        offset: str = "",
    ) -> Dict[str, Any]:
        """Return historical funding rates for a perpetual instrument."""
        if not instrument_name:
            return err_response("instrument_name is required")
        try:
            return ok_response(
                client.get_funding_history(instrument_name, start_time, end_time, limit, offset)
            )
        except AevoApiError as exc:
            return err_response("failed to fetch funding history", str(exc))
        except Exception as exc:
            return err_response("failed to fetch funding history", str(exc))

    @mcp.tool()
    def trade_history(instrument_name: str) -> Dict[str, Any]:
        """Return recent public trades for an instrument."""
        if not instrument_name:
            return err_response("instrument_name is required")
        try:
            return ok_response(client.get_trade_history_public(instrument_name))
        except AevoApiError as exc:
            return err_response("failed to fetch trade history", str(exc))
        except Exception as exc:
            return err_response("failed to fetch trade history", str(exc))

    @mcp.tool()
    def statistics() -> Dict[str, Any]:
        """Return exchange-wide market statistics (volume, open interest, etc)."""
        try:
            return ok_response(client.get_statistics())
        except AevoApiError as exc:
            return err_response("failed to fetch statistics", str(exc))
        except Exception as exc:
            return err_response("failed to fetch statistics", str(exc))

    @mcp.tool()
    def index_price(asset: str) -> Dict[str, Any]:
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
        limit: str = "",
    ) -> Dict[str, Any]:
        """Return historical index prices for an asset."""
        if not asset:
            return err_response("asset is required")
        try:
            return ok_response(
                client.get_index_history(asset, resolution, start_time, end_time, limit)
            )
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
        limit: str = "",
    ) -> Dict[str, Any]:
        """Return historical mark prices for an instrument."""
        if not instrument_name:
            return err_response("instrument_name is required")
        try:
            return ok_response(
                client.get_mark_history(instrument_name, resolution, start_time, end_time, limit)
            )
        except AevoApiError as exc:
            return err_response("failed to fetch mark history", str(exc))
        except Exception as exc:
            return err_response("failed to fetch mark history", str(exc))

    @mcp.tool()
    def settlement_history(
        asset: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: str = "",
    ) -> Dict[str, Any]:
        """Return settlement history, optionally filtered by asset."""
        try:
            return ok_response(
                client.get_settlement_history(asset, start_time, end_time, limit)
            )
        except AevoApiError as exc:
            return err_response("failed to fetch settlement history", str(exc))
        except Exception as exc:
            return err_response("failed to fetch settlement history", str(exc))

    @mcp.tool()
    def expiries(asset: str) -> Dict[str, Any]:
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
    def server_time() -> Dict[str, Any]:
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
