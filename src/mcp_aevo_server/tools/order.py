from __future__ import annotations

import time
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from ..client import AevoApiError
from ..config import AevoMcpConfig
from ..signing import sign_order_payload
from ..utils import err_response, ok_response, parse_int_field
from ..utils.addressing import resolve_account_address


def _build_order_payload(
    config: AevoMcpConfig,
    client: Any,
    instrument: str,
    is_buy: bool,
    amount: str,
    limit_price: str,
    salt: str,
    order_timestamp: int,
    post_only: bool,
    reduce_only: bool,
    time_in_force: str,
    mmp: bool,
) -> Dict[str, Any]:
    if not config.account_private_key:
        raise RuntimeError("AEVO_ACCOUNT_PRIVATE_KEY is required")
    if not config.signing_key_private_key:
        raise RuntimeError("AEVO_SIGNING_KEY_PRIVATE_KEY is required")

    account_address = resolve_account_address(config)
    instrument_id = client.resolve_instrument_id(instrument)
    if not instrument_id:
        raise RuntimeError(f"instrument not found: {instrument}")

    return sign_order_payload(
        network=config.network,
        account=account_address,
        is_buy=is_buy,
        price=limit_price,
        amount=amount,
        instrument_id=instrument_id,
        signing_key_private_key=config.signing_key_private_key,
        timestamp=order_timestamp or int(time.time()),
        salt=parse_int_field(salt, "salt") if salt else None,
        post_only=post_only,
        reduce_only=reduce_only,
        time_in_force=time_in_force,
        mmp=mmp,
    )


def register_order_tools(mcp: FastMCP, client: Any, config: AevoMcpConfig) -> Dict[str, Any]:
    def _require_credentials() -> None:
        if not client.has_credentials:
            raise RuntimeError("missing AEVO_API_KEY/AEVO_API_SECRET; call register_account first")

    @mcp.tool()
    def list_orders() -> Dict[str, Any]:
        """Fetch all current user orders."""
        try:
            _require_credentials()
            return ok_response(client.get_orders())
        except (RuntimeError, AevoApiError) as exc:
            return err_response("failed to fetch orders", str(exc))
        except Exception as exc:
            return err_response("failed to fetch orders", str(exc))

    @mcp.tool()
    def get_order(order_id: str) -> Dict[str, Any]:
        """Fetch one order by id."""
        if not order_id:
            return err_response("order_id is required")
        try:
            _require_credentials()
            return ok_response(client.get_order(order_id))
        except (RuntimeError, AevoApiError) as exc:
            return err_response("failed to fetch order", str(exc))
        except Exception as exc:
            return err_response("failed to fetch order", str(exc))

    @mcp.tool()
    def build_order(
        instrument: str,
        is_buy: bool,
        amount: str,
        limit_price: str,
        salt: str = "",
        order_timestamp: int = 0,
        post_only: bool = False,
        reduce_only: bool = False,
        time_in_force: str = "GTC",
        mmp: bool = False,
    ) -> Dict[str, Any]:
        """Build and return a signed order payload (no submission)."""
        try:
            payload = _build_order_payload(
                config=config,
                client=client,
                instrument=instrument,
                is_buy=is_buy,
                amount=amount,
                limit_price=limit_price,
                salt=salt,
                order_timestamp=order_timestamp,
                post_only=post_only,
                reduce_only=reduce_only,
                time_in_force=time_in_force,
                mmp=mmp,
            )
            return ok_response(payload)
        except (RuntimeError, ValueError, AevoApiError) as exc:
            return err_response("failed to build order payload", str(exc))
        except Exception as exc:
            return err_response("failed to build order payload", str(exc))

    @mcp.tool()
    def create_order(
        instrument: str,
        is_buy: bool,
        amount: str,
        limit_price: str,
        salt: str = "",
        order_timestamp: int = 0,
        post_only: bool = False,
        reduce_only: bool = False,
        time_in_force: str = "GTC",
        mmp: bool = False,
    ) -> Dict[str, Any]:
        """Build a signed order payload and submit it."""
        try:
            _require_credentials()
            payload = _build_order_payload(
                config=config,
                client=client,
                instrument=instrument,
                is_buy=is_buy,
                amount=amount,
                limit_price=limit_price,
                salt=salt,
                order_timestamp=order_timestamp,
                post_only=post_only,
                reduce_only=reduce_only,
                time_in_force=time_in_force,
                mmp=mmp,
            )
            return ok_response(client.create_order(payload))
        except (RuntimeError, ValueError, AevoApiError) as exc:
            return err_response("failed to create order", str(exc))
        except Exception as exc:
            return err_response("failed to create order", str(exc))

    @mcp.tool()
    def cancel_order(order_id: str) -> Dict[str, Any]:
        """Cancel one order."""
        if not order_id:
            return err_response("order_id is required")
        try:
            _require_credentials()
            return ok_response(client.cancel_order(order_id=order_id))
        except (RuntimeError, AevoApiError) as exc:
            return err_response("failed to cancel order", str(exc))
        except Exception as exc:
            return err_response("failed to cancel order", str(exc))

    @mcp.tool()
    def cancel_orders(order_ids: list[str], instrument_type: str = "") -> Dict[str, Any]:
        """Cancel many orders in one request."""
        if not order_ids:
            return err_response("order_ids is required")
        try:
            _require_credentials()
            return ok_response(client.cancel_orders(order_ids=order_ids, instrument_type=instrument_type or None))
        except (RuntimeError, AevoApiError) as exc:
            return err_response("failed to cancel orders", str(exc))
        except Exception as exc:
            return err_response("failed to cancel orders", str(exc))

    @mcp.tool()
    def cancel_all(asset: str = "", instrument_type: str = "") -> Dict[str, Any]:
        """Cancel all open orders for the account."""
        try:
            _require_credentials()
            return ok_response(
                client.cancel_all_orders(
                    asset=asset or None,
                    instrument_type=instrument_type or None,
                )
            )
        except (RuntimeError, AevoApiError) as exc:
            return err_response("failed to cancel all orders", str(exc))
        except Exception as exc:
            return err_response("failed to cancel all orders", str(exc))

    return {
        "list_orders": list_orders,
        "get_order": get_order,
        "build_order": build_order,
        "create_order": create_order,
        "cancel_order": cancel_order,
        "cancel_orders": cancel_orders,
        "cancel_all": cancel_all,
        "_build_order_payload": lambda **kwargs: _build_order_payload(config=config, client=client, **kwargs),
    }
