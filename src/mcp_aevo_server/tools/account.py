from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import AevoApiError
from ..config import AevoMcpConfig
from ..signing import derive_address
from ..utils import err_response, ok_response
from ..utils.addressing import resolve_wallet_address


def status_payload(config: AevoMcpConfig, client: Any) -> dict[str, Any]:
    try:
        wallet_address = resolve_wallet_address(config)
    except RuntimeError:
        wallet_address = config.wallet_address or ""

    signing_key_address = ""
    if config.signing_key_private_key:
        try:
            signing_key_address = derive_address(config.signing_key_private_key)
        except Exception:
            pass

    return {
        "environment": config.environment,
        "api_base_url": config.api_base_url,
        "wallet_address": wallet_address,
        "signing_key": signing_key_address,
        "has_signing_keys": bool(config.wallet_private_key and config.signing_key_private_key),
        "has_api_credentials": client.has_credentials,
        "mcp_host": config.mcp_host,
        "mcp_port": config.mcp_port,
        "mcp_path": config.mcp_path,
        "mcp_transport": config.mcp_transport,
    }


def _pick(d: dict, keys: list[str]) -> dict:
    return {k: d[k] for k in keys if k in d}


ACCOUNT_FIELDS = [
    "account",
    "balance",
    "available_balance",
    "equity",
    "margin_usage",
    "collaterals",
    "username",
    "email",
]

PORTFOLIO_FIELDS = ["balance", "pnl", "unrealized_pnl", "greeks", "positions"]

POSITION_FIELDS = [
    "instrument_name",
    "instrument_type",
    "side",
    "amount",
    "mark_price",
    "entry_price",
    "unrealized_pnl",
    "liquidation_price",
    "asset",
]


def require_api_credentials(client: Any) -> None:
    if not client.has_credentials:
        raise RuntimeError("missing AEVO_API_KEY/AEVO_API_SECRET; call register_account first")


def register_account_tools(mcp: FastMCP, client: Any, config: AevoMcpConfig) -> dict[str, Any]:
    @mcp.tool()
    def status() -> dict[str, Any]:
        """Return MCP runtime and AEVO identity context."""
        return ok_response(status_payload(config, client))

    @mcp.tool()
    def account() -> dict[str, Any]:
        """Return account summary: balance, available_balance, equity, margin_usage, collaterals."""
        try:
            require_api_credentials(client)
            raw = client.get_account()
            return ok_response(_pick(raw, ACCOUNT_FIELDS) if isinstance(raw, dict) else raw)
        except (RuntimeError, AevoApiError) as exc:
            return err_response("failed to fetch account", str(exc))
        except Exception as exc:
            return err_response("failed to fetch account", str(exc))

    @mcp.tool()
    def portfolio() -> dict[str, Any]:
        """Return portfolio summary: balance, pnl, unrealized_pnl, greeks."""
        try:
            require_api_credentials(client)
            raw = client.get_portfolio()
            return ok_response(_pick(raw, PORTFOLIO_FIELDS) if isinstance(raw, dict) else raw)
        except (RuntimeError, AevoApiError) as exc:
            return err_response("failed to fetch portfolio", str(exc))
        except Exception as exc:
            return err_response("failed to fetch portfolio", str(exc))

    @mcp.tool()
    def positions() -> dict[str, Any]:
        """Return open positions: instrument_name, side, amount, mark_price, entry_price, unrealized_pnl, liquidation_price."""
        try:
            require_api_credentials(client)
            raw = client.get_positions()
            return ok_response([_pick(p, POSITION_FIELDS) for p in raw] if isinstance(raw, list) else raw)
        except (RuntimeError, AevoApiError) as exc:
            return err_response("failed to fetch positions", str(exc))
        except Exception as exc:
            return err_response("failed to fetch positions", str(exc))

    @mcp.tool()
    def account_trade_history(
        start_time: str = "",
        end_time: str = "",
        limit: str = "50",
        offset: str = "",
        trade_types: str = "",
        instrument_name: str = "",
        instrument_type: str = "",
        asset: str = "",
    ) -> dict[str, Any]:
        """Return trade (fill) history for the authenticated account."""
        try:
            require_api_credentials(client)
            return ok_response(
                client.get_account_trade_history(
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit,
                    offset=offset,
                    trade_types=trade_types,
                    instrument_name=instrument_name,
                    instrument_type=instrument_type,
                    asset=asset,
                )
            )
        except (RuntimeError, AevoApiError) as exc:
            return err_response("failed to fetch account trade history", str(exc))
        except Exception as exc:
            return err_response("failed to fetch account trade history", str(exc))

    @mcp.tool()
    def order_history(
        start_time: str = "",
        end_time: str = "",
        limit: str = "50",
        offset: str = "",
        instrument_name: str = "",
        instrument_type: str = "",
        asset: str = "",
    ) -> dict[str, Any]:
        """Return historical orders for the authenticated account."""
        try:
            require_api_credentials(client)
            return ok_response(
                client.get_order_history(
                    start_time=start_time,
                    end_time=end_time,
                    limit=limit,
                    offset=offset,
                    instrument_name=instrument_name,
                    instrument_type=instrument_type,
                    asset=asset,
                )
            )
        except (RuntimeError, AevoApiError) as exc:
            return err_response("failed to fetch order history", str(exc))
        except Exception as exc:
            return err_response("failed to fetch order history", str(exc))

    return {
        "status": status,
        "account": account,
        "portfolio": portfolio,
        "positions": positions,
        "account_trade_history": account_trade_history,
        "order_history": order_history,
        "status_payload": lambda: status_payload(config, client),
        "require_api_credentials": lambda: require_api_credentials(client),
    }
