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

    return {
        "assets": assets,
        "markets": markets,
        "orderbook": orderbook,
        "instrument": instrument,
    }
