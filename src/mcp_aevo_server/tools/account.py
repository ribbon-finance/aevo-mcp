from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from ..config import AevoMcpConfig
from ..session_auth import SessionAuthStore
from ..signing import derive_address
from ..utils.addressing import resolve_wallet_address
from ..utils.response import pick
from ..utils.validation import require_api_credentials, resolve_auth


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
        "supports_runtime_credentials": True,
        "mcp_host": config.mcp_host,
        "mcp_port": config.mcp_port,
        "mcp_path": config.mcp_path,
        "mcp_transport": config.mcp_transport,
    }


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


def register_account_tools(
    mcp: FastMCP, client: Any, config: AevoMcpConfig, auth_store: SessionAuthStore | None = None
) -> dict[str, Any]:
    def _session_credentials(ctx: Context | None) -> tuple[str, str]:
        if not auth_store:
            return "", ""
        creds = auth_store.get_for_context(ctx)
        if not creds:
            return "", ""
        return creds.api_key, creds.api_secret

    def _session_signing_status(ctx: Context | None) -> bool:
        if not auth_store:
            return False
        creds = auth_store.get_for_context(ctx)
        if not creds:
            return False
        return creds.has_signing_credentials

    @mcp.tool(
        name="aevo_get_status",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
    )
    async def status(ctx: Context | None = None) -> dict:
        """Return MCP runtime and AEVO identity context.

        Shows environment, wallet address, signing key status, API credential status,
        session auth state, and transport configuration. Use this to verify connectivity.
        """
        payload = status_payload(config, client)
        session_api_key, session_api_secret = _session_credentials(ctx)
        payload["session_scoped_auth_enabled"] = bool(auth_store)
        payload["session_authenticated"] = bool(session_api_key and session_api_secret)
        payload["session_has_signing_keys"] = _session_signing_status(ctx)
        payload["connected_client_id"] = getattr(ctx, "client_id", "") if ctx is not None else ""
        return payload

    @mcp.tool(
        name="aevo_onboard",
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    async def onboard(ctx: Context | None = None) -> dict:
        """Start or resume an AEVO session. Call this at the beginning of every session.

        Returns the current session state and tells you what to do next:
        - If credentials already exist: returns status summary — proceed with trading.
        - If credentials are missing: returns exactly which credentials to collect
          from the user and how to authenticate.

        This is the recommended entry point for any AEVO agent interaction.
        """
        # Check env-level credentials
        env_has_api = client.has_credentials
        env_has_signing = bool(config.wallet_private_key and config.signing_key_private_key)
        env_wallet = config.wallet_address or ""

        # Check session-level credentials
        session_creds = auth_store.get_for_context(ctx) if auth_store else None
        session_has_api = bool(session_creds and session_creds.has_api_credentials)
        session_has_signing = bool(session_creds and session_creds.has_signing_credentials)
        session_wallet = (session_creds.wallet_address if session_creds else "") or ""

        has_api = env_has_api or session_has_api
        has_signing = env_has_signing or session_has_signing
        wallet = session_wallet or env_wallet
        can_trade = has_api and has_signing and bool(wallet)

        if can_trade:
            return {
                "status": "ready",
                "message": "Session is fully authenticated. Ready to trade.",
                "can_read_account": True,
                "can_trade": True,
                "wallet_address": wallet,
                "credential_source": "session" if session_has_api else "environment",
                "actions": [
                    "Proceed with trading — use aevo_list_markets, aevo_get_account, etc.",
                    "To change credentials, call aevo_authenticate with new values.",
                    "To clear session credentials, call aevo_clear_auth.",
                ],
            }

        if has_api and not can_trade:
            missing = []
            if not wallet:
                missing.append("wallet_address")
            if not has_signing:
                missing.append("signing_key_private_key")
            return {
                "status": "partial",
                "message": (
                    "API credentials found — you can read account data. "
                    "But order creation requires additional credentials."
                ),
                "can_read_account": True,
                "can_trade": False,
                "credential_source": "session" if session_has_api else "environment",
                "missing_for_trading": missing,
                "action": (
                    "Ask the user for the missing fields and call aevo_authenticate. "
                    "Credentials are available at https://app.aevo.xyz/settings"
                ),
            }

        # No credentials at all
        return {
            "status": "unauthenticated",
            "message": "No credentials found. Please collect credentials from the user to get started.",
            "can_read_account": False,
            "can_trade": False,
            "credentials_needed": {
                "required_for_account_access": ["api_key", "api_secret"],
                "required_for_trading": [
                    "api_key",
                    "api_secret",
                    "wallet_address",
                    "signing_key_private_key",
                ],
                "optional": ["wallet_private_key (derives wallet_address if not provided)"],
            },
            "credentials_url": "https://app.aevo.xyz/settings",
            "action": (
                "Ask the user for their credentials (available at https://app.aevo.xyz/settings), "
                "then call aevo_authenticate with all collected values."
            ),
        }

    @mcp.tool(
        name="aevo_authenticate",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    async def authenticate(
        api_key: str = "",
        api_secret: str = "",
        wallet_address: str = "",
        wallet_private_key: str = "",
        signing_key_private_key: str = "",
        ctx: Context | None = None,
    ) -> dict:
        """Store credentials for the current MCP client session (memory-only, not persisted).

        Call this once per session to enable authenticated operations without passing
        credentials to every tool call. Credentials are scoped to the current client session.

        **Credential tiers — what each unlocks:**

        1. `api_key` + `api_secret` → read-only account data (balances, positions,
           order history, trade fills).
        2. Add `wallet_address` + `signing_key_private_key` → order creation, order
           cancellation, and account registration (signs EIP-712 payloads on-chain).
        3. Add `wallet_private_key` → derives wallet_address automatically if not
           provided, and enables register_account bootstrap.

        For the **full trading experience**, provide all five fields. At minimum,
        provide `api_key`, `api_secret`, `wallet_address`, and
        `signing_key_private_key`.

        All credentials can be found at https://app.aevo.xyz/settings

        Args:
            api_key: AEVO API key (required for any authenticated endpoint).
            api_secret: AEVO API secret (required, paired with api_key).
            wallet_address: Ethereum wallet address (required for order signing).
            wallet_private_key: Wallet private key — used to derive wallet_address
                if not provided and for account registration.
            signing_key_private_key: AEVO signing key private key (required for
                creating/cancelling orders — signs EIP-712 order payloads).
        """
        if not auth_store:
            raise RuntimeError("session auth is not enabled on this server")
        if ctx is None:
            raise RuntimeError("session context is unavailable for this request")
        resolve_auth(api_key=api_key, api_secret=api_secret)
        creds = auth_store.upsert_for_context(
            ctx,
            api_key=api_key,
            api_secret=api_secret,
            wallet_address=wallet_address,
            wallet_private_key=wallet_private_key,
            signing_key_private_key=signing_key_private_key,
        )
        if creds is None:
            raise RuntimeError("failed to resolve session identity")
        can_trade = creds.has_signing_credentials and bool(
            creds.wallet_address or creds.wallet_private_key
        )
        result: dict = {
            "stored": True,
            "session_authenticated": creds.has_api_credentials,
            "session_has_signing_keys": creds.has_signing_credentials,
            "can_read_account": creds.has_api_credentials,
            "can_trade": can_trade,
        }
        if creds.has_api_credentials and not can_trade:
            missing = []
            if not creds.wallet_address and not creds.wallet_private_key:
                missing.append("wallet_address (or wallet_private_key to derive it)")
            if not creds.signing_key_private_key:
                missing.append("signing_key_private_key")
            result["missing_for_trading"] = missing
            result["hint"] = (
                "Call aevo_authenticate again with the missing fields to enable "
                "order creation and cancellation."
            )
        return result

    @mcp.tool(
        name="aevo_clear_auth",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False),
    )
    async def clear_auth(ctx: Context | None = None) -> dict:
        """Clear credentials for the current MCP client session.

        After clearing, authenticated operations will fail until credentials are
        provided again via aevo_authenticate or per-call api_key/api_secret params.
        """
        if not auth_store:
            raise RuntimeError("session auth is not enabled on this server")
        if ctx is None:
            raise RuntimeError("session context is unavailable for this request")
        return {"cleared": auth_store.clear_for_context(ctx)}

    @mcp.tool(
        name="aevo_get_account",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
    )
    async def account(api_key: str = "", api_secret: str = "", ctx: Context | None = None) -> dict:
        """Return account summary: balance, available_balance, equity, margin_usage, collaterals.

        Requires API credentials via session auth, env vars, or per-call params.

        Args:
            api_key: Optional per-call API key override.
            api_secret: Optional per-call API secret override.
        """
        session_api_key, session_api_secret = _session_credentials(ctx)
        auth = require_api_credentials(
            client,
            api_key=api_key,
            api_secret=api_secret,
            session_api_key=session_api_key,
            session_api_secret=session_api_secret,
        )
        raw = await client.get_account(auth=auth)
        return pick(raw, ACCOUNT_FIELDS) if isinstance(raw, dict) else raw

    @mcp.tool(
        name="aevo_get_portfolio",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
    )
    async def portfolio(api_key: str = "", api_secret: str = "", ctx: Context | None = None) -> dict:
        """Return portfolio summary: balance, pnl, unrealized_pnl, greeks.

        Args:
            api_key: Optional per-call API key override.
            api_secret: Optional per-call API secret override.
        """
        session_api_key, session_api_secret = _session_credentials(ctx)
        auth = require_api_credentials(
            client,
            api_key=api_key,
            api_secret=api_secret,
            session_api_key=session_api_key,
            session_api_secret=session_api_secret,
        )
        raw = await client.get_portfolio(auth=auth)
        return pick(raw, PORTFOLIO_FIELDS) if isinstance(raw, dict) else raw

    @mcp.tool(
        name="aevo_get_positions",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
    )
    async def positions(api_key: str = "", api_secret: str = "", ctx: Context | None = None) -> list:
        """Return open positions with key fields per position.

        Fields: instrument_name, side, amount, mark_price, entry_price,
        unrealized_pnl, liquidation_price.

        Args:
            api_key: Optional per-call API key override.
            api_secret: Optional per-call API secret override.
        """
        session_api_key, session_api_secret = _session_credentials(ctx)
        auth = require_api_credentials(
            client,
            api_key=api_key,
            api_secret=api_secret,
            session_api_key=session_api_key,
            session_api_secret=session_api_secret,
        )
        raw = await client.get_positions(auth=auth)
        return [pick(p, POSITION_FIELDS) for p in raw] if isinstance(raw, list) else raw

    @mcp.tool(
        name="aevo_update_leverage",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True
        ),
    )
    async def update_leverage(
        instrument_name: str,
        leverage: int,
        api_key: str = "",
        api_secret: str = "",
        ctx: Context | None = None,
    ) -> dict:
        """Update the leverage multiplier for a specific instrument.

        Args:
            instrument_name: Instrument to update (e.g. "ETH-PERP", "BTC-PERP").
            leverage: Leverage multiplier (e.g. 5 for 5x).
            api_key: Optional per-call API key override.
            api_secret: Optional per-call API secret override.
        """
        session_api_key, session_api_secret = _session_credentials(ctx)
        auth = require_api_credentials(
            client,
            api_key=api_key,
            api_secret=api_secret,
            session_api_key=session_api_key,
            session_api_secret=session_api_secret,
        )
        instrument_id = await client.resolve_instrument_id(instrument_name)
        if not instrument_id:
            raise RuntimeError(f"instrument not found: {instrument_name}")
        return await client.update_leverage(
            instrument_id=int(instrument_id), leverage=leverage, auth=auth
        )

    @mcp.tool(
        name="aevo_get_trade_fills",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
    )
    async def account_trade_history(
        start_time: str = "",
        end_time: str = "",
        limit: str = "50",
        offset: str = "",
        trade_types: str = "",
        instrument_name: str = "",
        instrument_type: str = "",
        asset: str = "",
        api_key: str = "",
        api_secret: str = "",
        ctx: Context | None = None,
    ) -> list:
        """Return trade (fill) history for the authenticated account.

        Args:
            start_time: Start timestamp filter (unix seconds).
            end_time: End timestamp filter (unix seconds).
            limit: Max records (default 50).
            offset: Pagination offset.
            trade_types: Filter by trade type.
            instrument_name: Filter by instrument.
            instrument_type: Filter by type (e.g. "PERPETUAL").
            asset: Filter by asset (e.g. "ETH").
            api_key: Optional per-call API key override.
            api_secret: Optional per-call API secret override.
        """
        session_api_key, session_api_secret = _session_credentials(ctx)
        auth = require_api_credentials(
            client,
            api_key=api_key,
            api_secret=api_secret,
            session_api_key=session_api_key,
            session_api_secret=session_api_secret,
        )
        return await client.get_account_trade_history(
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
            trade_types=trade_types,
            instrument_name=instrument_name,
            instrument_type=instrument_type,
            asset=asset,
            auth=auth,
        )

    @mcp.tool(
        name="aevo_get_order_history",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True),
    )
    async def order_history(
        start_time: str = "",
        end_time: str = "",
        limit: str = "50",
        offset: str = "",
        instrument_name: str = "",
        instrument_type: str = "",
        asset: str = "",
        api_key: str = "",
        api_secret: str = "",
        ctx: Context | None = None,
    ) -> list:
        """Return historical orders for the authenticated account.

        Args:
            start_time: Start timestamp filter (unix seconds).
            end_time: End timestamp filter (unix seconds).
            limit: Max records (default 50).
            offset: Pagination offset.
            instrument_name: Filter by instrument.
            instrument_type: Filter by type (e.g. "PERPETUAL").
            asset: Filter by asset (e.g. "ETH").
            api_key: Optional per-call API key override.
            api_secret: Optional per-call API secret override.
        """
        session_api_key, session_api_secret = _session_credentials(ctx)
        auth = require_api_credentials(
            client,
            api_key=api_key,
            api_secret=api_secret,
            session_api_key=session_api_key,
            session_api_secret=session_api_secret,
        )
        return await client.get_order_history(
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
            instrument_name=instrument_name,
            instrument_type=instrument_type,
            asset=asset,
            auth=auth,
        )

    return {
        "status": status,
        "onboard": onboard,
        "authenticate": authenticate,
        "clear_auth": clear_auth,
        "account": account,
        "portfolio": portfolio,
        "positions": positions,
        "update_leverage": update_leverage,
        "account_trade_history": account_trade_history,
        "order_history": order_history,
        "status_payload": lambda: status_payload(config, client),
        "require_api_credentials": lambda api_key="", api_secret="", ctx=None: require_api_credentials(
            client,
            api_key=api_key,
            api_secret=api_secret,
            session_api_key=_session_credentials(ctx)[0],
            session_api_secret=_session_credentials(ctx)[1],
        ),
    }
