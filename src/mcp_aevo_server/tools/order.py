from __future__ import annotations

import time
from dataclasses import is_dataclass, replace
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from ..config import AevoMcpConfig
from ..session_auth import SessionAuthStore
from ..signing import sign_order_payload
from ..utils.addressing import resolve_wallet_address
from ..utils.response import pick
from ..utils.validation import parse_int_field, resolve_auth


def _config_with_overrides(config: Any, **overrides: Any) -> Any:
    effective: dict[str, Any] = {}
    for key, value in overrides.items():
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                effective[key] = normalized
        elif value is not None:
            effective[key] = value

    if not effective:
        return config
    if is_dataclass(config):
        return replace(config, **effective)
    merged = dict(vars(config))
    merged.update(effective)
    return type(config)(**merged)


async def _build_order_payload(
    config: Any,
    client: Any,
    instrument_name: str,
    is_buy: bool,
    amount: str,
    limit_price: str,
    salt: str,
    order_timestamp: int,
    post_only: bool,
    reduce_only: bool,
    time_in_force: str,
    mmp: bool,
    stop: str = "",
    trigger: str = "",
    close_position: bool = False,
    partial_position: bool = False,
) -> dict[str, Any]:
    """Build a signed order payload and resolve instrument id asynchronously."""
    if not config.wallet_address and not config.wallet_private_key:
        raise RuntimeError(
            "wallet_address is required for order signing. "
            "Call aevo_authenticate with wallet_address (or wallet_private_key to derive it). "
            "Credentials can be found at https://app.aevo.xyz/settings"
        )
    if not config.signing_key_private_key:
        raise RuntimeError(
            "signing_key_private_key is required for order signing. "
            "Call aevo_authenticate with your AEVO signing key private key. "
            "Credentials can be found at https://app.aevo.xyz/settings"
        )

    account_address = resolve_wallet_address(config)
    instrument_id = await client.resolve_instrument_id(instrument_name)
    if not instrument_id:
        raise RuntimeError(f"instrument not found: {instrument_name}")

    payload = sign_order_payload(
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

    if stop:
        payload["stop"] = stop
    if trigger:
        payload["trigger"] = trigger
    if close_position:
        payload["close_position"] = True
    if partial_position:
        payload["partial_position"] = True

    return payload


ORDER_FIELDS = [
    "order_id",
    "instrument_name",
    "instrument_id",
    "side",
    "is_buy",
    "amount",
    "filled",
    "limit_price",
    "avg_price",
    "order_type",
    "status",
    "created_at",
]


def register_order_tools(
    mcp: FastMCP, client: Any, config: AevoMcpConfig, auth_store: SessionAuthStore | None = None
) -> dict[str, Any]:
    def _session_creds(ctx: Context | None):
        if not auth_store:
            return None
        return auth_store.get_for_context(ctx)

    def _runtime_config(ctx: Context | None) -> Any:
        creds = _session_creds(ctx)
        return _config_with_overrides(
            config,
            wallet_address=creds.wallet_address if creds else "",
            signing_key_private_key=creds.signing_key_private_key if creds else "",
            wallet_private_key=creds.wallet_private_key if creds else "",
        )

    def _require_credentials(
        api_key: str = "", api_secret: str = "", ctx: Context | None = None
    ) -> tuple[str, str] | None:
        creds = _session_creds(ctx)
        auth = resolve_auth(
            api_key=api_key,
            api_secret=api_secret,
            session_api_key=creds.api_key if creds else "",
            session_api_secret=creds.api_secret if creds else "",
        )
        if auth is None and not client.has_credentials:
            raise RuntimeError(
                "missing AEVO_API_KEY/AEVO_API_SECRET; provide api_key/api_secret or call register_account"
            )
        return auth

    @mcp.tool(
        name="aevo_list_orders",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
    )
    async def list_orders(api_key: str = "", api_secret: str = "", ctx: Context | None = None) -> list:
        """Fetch all current open orders.

        Returns key fields per order: order_id, instrument_name, side, amount,
        filled, limit_price, status, created_at.

        Args:
            api_key: Optional per-call API key override.
            api_secret: Optional per-call API secret override.
        """
        auth = _require_credentials(api_key=api_key, api_secret=api_secret, ctx=ctx)
        raw = await client.get_orders(auth=auth)
        return [pick(o, ORDER_FIELDS) for o in raw] if isinstance(raw, list) else raw

    @mcp.tool(
        name="aevo_get_order",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
    )
    async def get_order(order_id: str, api_key: str = "", api_secret: str = "", ctx: Context | None = None) -> dict:
        """Fetch one order by its order_id.

        Returns: order_id, instrument_name, side, amount, filled, limit_price, status, created_at.

        Args:
            order_id: The order ID to look up.
            api_key: Optional per-call API key override.
            api_secret: Optional per-call API secret override.
        """
        auth = _require_credentials(api_key=api_key, api_secret=api_secret, ctx=ctx)
        raw = await client.get_order(order_id, auth=auth)
        return pick(raw, ORDER_FIELDS) if isinstance(raw, dict) else raw

    @mcp.tool(
        name="aevo_build_order",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
    )
    async def build_order(
        instrument_name: str,
        is_buy: bool,
        amount: str,
        limit_price: str,
        salt: str = "",
        order_timestamp: int = 0,
        post_only: bool = False,
        reduce_only: bool = False,
        time_in_force: str = "GTC",
        mmp: bool = False,
        stop: str = "",
        trigger: str = "",
        close_position: bool = False,
        partial_position: bool = False,
        ctx: Context | None = None,
    ) -> dict:
        """Build and return a signed order payload WITHOUT submitting it.

        Use human-readable values: amount in contracts (e.g. '0.5'),
        limit_price in USD (e.g. '67900'). The server auto-converts to AEVO's
        internal 6-decimal fixed-point format.

        Set stop/trigger for stop-loss or take-profit orders.

        Args:
            instrument_name: Instrument to trade (e.g. "ETH-PERP", "BTC-USDC").
            is_buy: True for buy, False for sell.
            amount: Order size in contracts (human-readable, e.g. "0.5").
            limit_price: Limit price in USD (human-readable, e.g. "67900").
            salt: Optional salt for order uniqueness.
            order_timestamp: Optional unix timestamp. Defaults to current time.
            post_only: If True, order will be rejected if it would trade immediately.
            reduce_only: If True, order can only reduce an existing position.
            time_in_force: "GTC" (Good Til Cancel), "IOC" (Immediate or Cancel), or "FOK" (Fill or Kill).
            mmp: Enable market maker protection.
            stop: Stop type (e.g. "STOP_LOSS", "TAKE_PROFIT").
            trigger: Trigger price for stop orders.
            close_position: If True, close entire position on fill.
            partial_position: If True, allow partial position close.
        """
        runtime_config = _runtime_config(ctx)
        return await _build_order_payload(
            config=runtime_config,
            client=client,
            instrument_name=instrument_name,
            is_buy=is_buy,
            amount=amount,
            limit_price=limit_price,
            salt=salt,
            order_timestamp=order_timestamp,
            post_only=post_only,
            reduce_only=reduce_only,
            time_in_force=time_in_force,
            mmp=mmp,
            stop=stop,
            trigger=trigger,
            close_position=close_position,
            partial_position=partial_position,
        )

    @mcp.tool(
        name="aevo_create_order",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
        ),
    )
    async def create_order(
        instrument_name: str,
        is_buy: bool,
        amount: str,
        limit_price: str,
        salt: str = "",
        order_timestamp: int = 0,
        post_only: bool = False,
        reduce_only: bool = False,
        time_in_force: str = "GTC",
        mmp: bool = False,
        stop: str = "",
        trigger: str = "",
        close_position: bool = False,
        partial_position: bool = False,
        api_key: str = "",
        api_secret: str = "",
        ctx: Context | None = None,
    ) -> dict:
        """Build a signed order payload and submit it to AEVO.

        Use human-readable values: amount in contracts (e.g. '0.5'),
        limit_price in USD (e.g. '67900'). Set stop/trigger for stop-loss
        or take-profit orders.

        CAUTION: This submits a real order. Verify parameters before calling.

        Args:
            instrument_name: Instrument to trade (e.g. "ETH-PERP").
            is_buy: True for buy, False for sell.
            amount: Order size in contracts.
            limit_price: Limit price in USD.
            salt: Optional salt for order uniqueness.
            order_timestamp: Optional unix timestamp.
            post_only: Reject if would trade immediately.
            reduce_only: Can only reduce existing position.
            time_in_force: "GTC", "IOC", or "FOK".
            mmp: Market maker protection.
            stop: Stop type.
            trigger: Trigger price.
            close_position: Close entire position on fill.
            partial_position: Allow partial position close.
            api_key: Optional per-call API key.
            api_secret: Optional per-call API secret.
        """
        auth = _require_credentials(api_key=api_key, api_secret=api_secret, ctx=ctx)
        runtime_config = _runtime_config(ctx)
        payload = await _build_order_payload(
            config=runtime_config,
            client=client,
            instrument_name=instrument_name,
            is_buy=is_buy,
            amount=amount,
            limit_price=limit_price,
            salt=salt,
            order_timestamp=order_timestamp,
            post_only=post_only,
            reduce_only=reduce_only,
            time_in_force=time_in_force,
            mmp=mmp,
            stop=stop,
            trigger=trigger,
            close_position=close_position,
            partial_position=partial_position,
        )
        return await client.create_order(payload, auth=auth)

    @mcp.tool(
        name="aevo_cancel_order",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True),
    )
    async def cancel_order(order_id: str, api_key: str = "", api_secret: str = "", ctx: Context | None = None) -> dict:
        """Cancel a single order by order_id.

        Args:
            order_id: The order ID to cancel.
            api_key: Optional per-call API key.
            api_secret: Optional per-call API secret.
        """
        auth = _require_credentials(api_key=api_key, api_secret=api_secret, ctx=ctx)
        return await client.cancel_order(order_id=order_id, auth=auth)

    @mcp.tool(
        name="aevo_cancel_orders",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True),
    )
    async def cancel_orders(
        order_ids: list[str],
        instrument_type: str = "",
        api_key: str = "",
        api_secret: str = "",
        ctx: Context | None = None,
    ) -> dict:
        """Cancel multiple orders in one request.

        Args:
            order_ids: List of order IDs to cancel.
            instrument_type: Optional instrument type filter.
            api_key: Optional per-call API key.
            api_secret: Optional per-call API secret.
        """
        auth = _require_credentials(api_key=api_key, api_secret=api_secret, ctx=ctx)
        return await client.cancel_orders(order_ids=order_ids, instrument_type=instrument_type or None, auth=auth)

    @mcp.tool(
        name="aevo_cancel_all_orders",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True),
    )
    async def cancel_all(
        asset: str = "",
        instrument_type: str = "",
        api_key: str = "",
        api_secret: str = "",
        ctx: Context | None = None,
    ) -> dict:
        """Cancel ALL open orders for the account. THIS IS DESTRUCTIVE.

        WARNING: This cancels every open order. Use with extreme caution.
        Consider aevo_cancel_order or aevo_cancel_orders for targeted cancellation.

        Args:
            asset: Optional filter — only cancel orders for this asset.
            instrument_type: Optional filter — only cancel orders of this type.
            api_key: Optional per-call API key.
            api_secret: Optional per-call API secret.
        """
        auth = _require_credentials(api_key=api_key, api_secret=api_secret, ctx=ctx)
        return await client.cancel_all_orders(
            asset=asset or None,
            instrument_type=instrument_type or None,
            auth=auth,
        )

    return {
        "list_orders": list_orders,
        "get_order": get_order,
        "build_order": build_order,
        "create_order": create_order,
        "cancel_order": cancel_order,
        "cancel_orders": cancel_orders,
        "cancel_all": cancel_all,
    }
