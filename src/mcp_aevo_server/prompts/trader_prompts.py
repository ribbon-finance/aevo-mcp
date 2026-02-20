from __future__ import annotations

from collections.abc import Callable
from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> dict[str, Callable]:
    @mcp.prompt()
    def trade_plan(
        symbol: str,
        side: str,
        amount: str,
        limit_price: str,
        time_in_force: str = "GTC",
        post_only: bool = False,
        reduce_only: bool = False,
    ) -> str:
        return (
            "AEVO TRADE PLAN\n"
            f"Symbol: {symbol}\n"
            f"Side: {side}\n"
            f"Amount: {amount} (human-readable, e.g. '0.5' = 0.5 contracts)\n"
            f"Limit price: {limit_price} (human-readable USD, e.g. '67900' = $67,900)\n"
            f"Time in force: {time_in_force.upper()}\n"
            f"Post-only: {post_only}\n"
            f"Reduce-only: {reduce_only}\n\n"
            "IMPORTANT: amount and limit_price use normal human-readable values.\n"
            "The server handles conversion to AEVO's internal format automatically.\n"
            "  Example: amount='0.5', limit_price='3000' for 0.5 contracts at $3,000.\n\n"
            "Execution sequence:\n"
            "1) Resolve instrument and market metadata via `markets`.\n"
            "2) Snapshot orderbook + account + positions.\n"
            "3) Validate preconditions with `risk_checklist`.\n"
            "4) Build payload with `build_order`.\n"
            "5) Submit with `create_order`.\n"
            "6) Verify result with `get_order`.\n"
        )

    @mcp.prompt()
    def risk_checklist() -> str:
        return (
            "Pre-trade checklist\n"
            "- Validate account is registered\n"
            "- Validate instrument and instrument_type\n"
            "- Validate margin and open risk\n"
            "- Validate maker/taker intent for post_only\n"
            "- Validate timestamp and salt are present\n"
        )

    @mcp.prompt()
    def cancel_plan(order_id: str = "") -> str:
        return (
            "CANCEL PLAN\n"
            f"Order id: {order_id or 'N/A'}\n\n"
            "Steps:\n"
            "1) If order id known, call `cancel_order(order_id)`.\n"
            "2) If order id unknown, call `list_orders` and filter by symbol.\n"
            "3) For batch operations use `cancel_orders` or `cancel_all`.\n"
            "4) Re-check with `list_orders` to confirm final state.\n"
        )

    @mcp.prompt()
    def onboarding_plan() -> str:
        return (
            "AEVO AGENT ONBOARDING\n"
            "1) Fill required key fields: account/private + signing keys.\n"
            "2) Run `status` to confirm identities and transport.\n"
            "3) Run `register_account` once (or set API creds in env).\n"
            "4) Inspect `assets` and `markets`.\n"
            "5) Inspect `account` + `positions` before opening risk.\n"
            "6) Verify first build with `build_order` and inspect signed payload.\n"
        )

    @mcp.prompt()
    def market_analysis(symbol: str = "ETH-PERP", asset: str = "ETH") -> str:
        return (
            "AEVO MARKET ANALYSIS\n"
            f"Symbol: {symbol}\n"
            f"Asset: {asset}\n\n"
            "Data-gathering sequence:\n"
            f"1) Fetch index price via `index_price(asset='{asset}')`.\n"
            f"2) Fetch current funding rate via `funding_rate(instrument_name='{symbol}')`.\n"
            f"3) Fetch funding history via `funding_history(instrument_name='{symbol}')`.\n"
            "4) Fetch exchange-wide statistics via `statistics()`.\n"
            f"5) Snapshot orderbook via `orderbook(instrument_name='{symbol}')`.\n"
            f"6) Fetch recent trades via `trade_history(instrument_name='{symbol}')`.\n"
            f"7) Fetch mark price history via `mark_history(instrument_name='{symbol}')`.\n\n"
            "Analysis:\n"
            "- Compare index vs mark price for premium/discount.\n"
            "- Evaluate funding rate trend (positive = longs pay, negative = shorts pay).\n"
            "- Assess orderbook depth and bid-ask spread.\n"
            "- Review recent trade flow for directional bias.\n"
            "- Summarize market conditions and potential trade setups.\n"
        )

    return {
        "trade_plan": trade_plan,
        "risk_checklist": risk_checklist,
        "cancel_plan": cancel_plan,
        "onboarding_plan": onboarding_plan,
        "market_analysis": market_analysis,
    }
