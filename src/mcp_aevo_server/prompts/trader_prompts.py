from __future__ import annotations

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> dict[str, Callable]:
    @mcp.prompt(description="Generate a step-by-step trade execution plan for placing an order on AEVO.")
    def trade_plan(
        symbol: str,
        side: str,
        amount: str,
        limit_price: str,
        leverage: int = 0,
        time_in_force: str = "GTC",
        post_only: bool = False,
        reduce_only: bool = False,
    ) -> str:
        leverage_line = f"Leverage: {leverage}x\n" if leverage else "Leverage: (not specified)\n"
        return (
            "AEVO TRADE PLAN\n"
            f"Symbol: {symbol}\n"
            f"Side: {side}\n"
            f"Amount: {amount} (human-readable, e.g. '0.5' = 0.5 contracts)\n"
            f"Limit price: {limit_price} (human-readable USD, e.g. '67900' = $67,900)\n"
            f"{leverage_line}"
            f"Time in force: {time_in_force.upper()}\n"
            f"Post-only: {post_only}\n"
            f"Reduce-only: {reduce_only}\n\n"
            "IMPORTANT: amount and limit_price use normal human-readable values.\n"
            "The server handles conversion to AEVO's internal format automatically.\n"
            "  Example: amount='0.5', limit_price='3000' for 0.5 contracts at $3,000.\n\n"
            "Execution sequence:\n"
            "0) Check `aevo_get_status` — if `can_trade` is false or signing keys are missing,\n"
            "   ask the user for wallet_address + signing_key_private_key and call `aevo_authenticate`.\n"
            "1) Resolve instrument and market metadata via `aevo_list_markets`.\n"
            "2) If leverage is specified, call `aevo_update_leverage(instrument_name, leverage)` first.\n"
            "3) Snapshot orderbook + account + positions.\n"
            "4) Validate preconditions with `risk_checklist`.\n"
            "5) Build payload with `aevo_build_order`.\n"
            "6) Submit with `aevo_create_order`.\n"
            "7) Verify result with `aevo_get_order`.\n"
        )

    @mcp.prompt(description="Pre-trade risk validation checklist for AEVO orders.")
    def risk_checklist() -> str:
        return (
            "Pre-trade checklist\n"
            "- Validate account is registered\n"
            "- Validate instrument and instrument_type\n"
            "- Validate margin and open risk\n"
            "- Validate maker/taker intent for post_only\n"
            "- Validate timestamp and salt are present\n"
        )

    @mcp.prompt(description="Generate a plan for cancelling one or more AEVO orders.")
    def cancel_plan(order_id: str = "") -> str:
        return (
            "CANCEL PLAN\n"
            f"Order id: {order_id or 'N/A'}\n\n"
            "Steps:\n"
            "1) If order id known, call `aevo_cancel_order(order_id)`.\n"
            "2) If order id unknown, call `aevo_list_orders` and filter by symbol.\n"
            "3) For batch operations use `aevo_cancel_orders` or `aevo_cancel_all_orders`.\n"
            "4) Re-check with `aevo_list_orders` to confirm final state.\n"
        )

    @mcp.prompt(description="Step-by-step onboarding guide for new AEVO agent sessions.")
    def onboarding_plan() -> str:
        return (
            "AEVO AGENT ONBOARDING\n\n"
            "Step 1 — Check session state:\n"
            "  Call `aevo_onboard` to check if credentials already exist.\n"
            "  It returns one of three states:\n"
            "    • 'ready'           → fully authenticated, skip to Step 4.\n"
            "    • 'partial'         → API creds exist but trading creds missing,\n"
            "                          ask user for the fields listed in missing_for_trading.\n"
            "    • 'unauthenticated' → no credentials, proceed to Step 2.\n\n"
            "Step 2 — Collect credentials from the user:\n"
            "  All credentials are available at https://app.aevo.xyz/settings\n\n"
            "  For the full trading experience, ask for:\n"
            "    • api_key                — AEVO API key\n"
            "    • api_secret             — AEVO API secret\n"
            "    • wallet_address         — Ethereum wallet address\n"
            "    • signing_key_private_key — AEVO signing key (for order signing)\n"
            "  Optional:\n"
            "    • wallet_private_key — derives wallet_address if not provided\n\n"
            "Step 3 — Authenticate:\n"
            "  Call `aevo_authenticate` with all collected credentials.\n"
            "  Verify `can_trade` is true in the response.\n\n"
            "Step 4 — Register (first time only):\n"
            "  Run `aevo_register_account` once to register signing key on-chain.\n\n"
            "Step 5 — Explore markets:\n"
            "  Inspect `aevo_list_assets` and `aevo_list_markets`.\n\n"
            "Step 6 — Check account state:\n"
            "  Inspect `aevo_get_account` + `aevo_get_positions` before opening risk.\n\n"
            "Step 7 — Test order signing:\n"
            "  Verify first build with `aevo_build_order` and inspect signed payload.\n"
        )

    @mcp.prompt(description="Comprehensive market analysis workflow for an AEVO instrument.")
    def market_analysis(symbol: str = "ETH-PERP", asset: str = "ETH") -> str:
        return (
            "AEVO MARKET ANALYSIS\n"
            f"Symbol: {symbol}\n"
            f"Asset: {asset}\n\n"
            "Data-gathering sequence:\n"
            f"1) Fetch index price via `aevo_get_index_price(asset='{asset}')`.\n"
            f"2) Fetch current funding rate via `aevo_get_funding_rate(instrument_name='{symbol}')`.\n"
            f"3) Fetch funding history via `aevo_get_funding_history(instrument_name='{symbol}')`.\n"
            "4) Fetch exchange-wide statistics via `aevo_get_statistics()`.\n"
            f"5) Snapshot orderbook via `aevo_get_orderbook(instrument_name='{symbol}')`.\n"
            f"6) Fetch recent trades via `aevo_get_trade_history(instrument_name='{symbol}')`.\n"
            f"7) Fetch mark price history via `aevo_get_mark_history(instrument_name='{symbol}')`.\n\n"
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
