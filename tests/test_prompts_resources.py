from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from mcp_aevo_server.prompts import register_options_prompts, register_prompts
from mcp_aevo_server.resources import register_market_resources


def test_prompts_can_be_registered_and_return_text():
    mcp = FastMCP("AEVO")
    prompts = register_prompts(mcp)

    assert "trade_plan" in prompts
    assert "risk_checklist" in prompts
    assert "cancel_plan" in prompts
    assert "onboarding_plan" in prompts
    assert "market_analysis" in prompts

    trade_output = prompts["trade_plan"](
        "BTC-USDC", "buy", "1", "50000", time_in_force="ioc", post_only=True, reduce_only=False
    )
    assert "AEVO TRADE PLAN" in trade_output
    assert "Symbol: BTC-USDC" in trade_output
    assert "Side: buy" in trade_output
    assert "Time in force: IOC" in trade_output
    assert "Post-only: True" in trade_output
    assert "Reduce-only: False" in trade_output
    assert "aevo_update_leverage" in trade_output
    assert "3) Snapshot orderbook + account + positions." in trade_output
    assert "Pre-trade checklist" in prompts["risk_checklist"]()


def test_cancel_plan_prompt_is_specific():
    mcp = FastMCP("AEVO")
    prompts = register_prompts(mcp)

    no_id = prompts["cancel_plan"]()
    with_id = prompts["cancel_plan"]("order-123")

    assert "Order id: N/A" in no_id
    assert "Order id: order-123" in with_id
    assert "1) If order id known, call `aevo_cancel_order(order_id)`." in no_id
    assert "3) For batch operations use `aevo_cancel_orders` or `aevo_cancel_all_orders`." in no_id


def test_onboarding_plan_prompt_contains_bootstrap_flow():
    mcp = FastMCP("AEVO")
    prompts = register_prompts(mcp)

    plan = prompts["onboarding_plan"]()
    assert "AEVO AGENT ONBOARDING" in plan
    assert "aevo_onboard" in plan
    assert "api_key" in plan
    assert "api_secret" in plan
    assert "wallet_address" in plan
    assert "signing_key_private_key" in plan
    assert "aevo_authenticate" in plan
    assert "can_trade" in plan
    assert "aevo_list_assets" in plan
    assert "aevo_list_markets" in plan
    assert "https://app.aevo.xyz/settings" in plan


def test_market_analysis_prompt():
    mcp = FastMCP("AEVO")
    prompts = register_prompts(mcp)

    output = prompts["market_analysis"]()
    assert "AEVO MARKET ANALYSIS" in output
    assert "Symbol: ETH-PERP" in output
    assert "Asset: ETH" in output
    assert "aevo_get_index_price" in output
    assert "aevo_get_funding_rate" in output
    assert "aevo_get_funding_history" in output
    assert "aevo_get_statistics" in output
    assert "aevo_get_trade_history" in output
    assert "aevo_get_mark_history" in output

    custom = prompts["market_analysis"](symbol="BTC-PERP", asset="BTC")
    assert "Symbol: BTC-PERP" in custom
    assert "Asset: BTC" in custom


def test_resources_can_be_registered_and_serialized():
    mcp = FastMCP("AEVO")

    def status_tool():
        return {"environment": "mainnet"}

    def market_tool():
        return [{"instrument_name": "BTC-USDC"}]

    def account_tool():
        return {"account": "ok"}

    resources = register_market_resources(
        mcp, status_tool=status_tool, market_tool=market_tool, account_tool=account_tool
    )

    status = json.loads(resources["resource_status"]())
    markets = json.loads(resources["resource_markets_summary"]())
    account = json.loads(resources["resource_account_overview"]())

    assert status == {"environment": "mainnet"}
    assert markets == [{"instrument_name": "BTC-USDC"}]
    assert account == {"account": "ok"}


def test_funding_resource():
    mcp = FastMCP("AEVO")

    calls = []

    def funding_tool(instrument_name):
        calls.append(instrument_name)
        return {"funding_rate": "0.0001"}

    resources = register_market_resources(
        mcp,
        status_tool=lambda: {},
        market_tool=lambda: {},
        account_tool=lambda: {},
        funding_tool=funding_tool,
    )

    result = json.loads(resources["resource_funding_snapshot"]())
    assert result["funding_rate"] == "0.0001"
    assert calls == ["ETH-PERP"]


def test_statistics_resource():
    mcp = FastMCP("AEVO")

    def statistics_tool():
        return {"daily_volume": "1000000"}

    resources = register_market_resources(
        mcp,
        status_tool=lambda: {},
        market_tool=lambda: {},
        account_tool=lambda: {},
        statistics_tool=statistics_tool,
    )

    result = json.loads(resources["resource_statistics_snapshot"]())
    assert result["daily_volume"] == "1000000"


def test_resources_backward_compatible_without_new_kwargs():
    mcp = FastMCP("AEVO")

    resources = register_market_resources(
        mcp,
        status_tool=lambda: {},
        market_tool=lambda: {},
        account_tool=lambda: {},
    )

    assert "resource_funding_snapshot" not in resources
    assert "resource_statistics_snapshot" not in resources


def test_options_prompts_register_all():
    mcp = FastMCP("AEVO")
    prompts = register_options_prompts(mcp)

    expected = [
        "options_strategy_selector",
        "options_straddle",
        "options_strangle",
        "options_bull_call_spread",
        "options_bear_put_spread",
        "options_iron_condor",
        "options_butterfly",
    ]
    for name in expected:
        assert name in prompts, f"missing prompt: {name}"


def test_options_strategy_selector_bullish():
    mcp = FastMCP("AEVO")
    prompts = register_options_prompts(mcp)

    output = prompts["options_strategy_selector"](asset="BTC", outlook="bullish")
    assert "BULLISH" in output
    assert "Bull Call Spread" in output
    assert "Long Call" in output
    assert "BTC" in output


def test_options_strategy_selector_neutral_high_vol():
    mcp = FastMCP("AEVO")
    prompts = register_options_prompts(mcp)

    output = prompts["options_strategy_selector"](asset="ETH", outlook="neutral", volatility_view="high")
    assert "HIGH VOLATILITY" in output
    assert "Long Straddle" in output
    assert "Long Strangle" in output


def test_options_strategy_selector_neutral_low_vol():
    mcp = FastMCP("AEVO")
    prompts = register_options_prompts(mcp)

    output = prompts["options_strategy_selector"](asset="ETH", outlook="neutral", volatility_view="low")
    assert "LOW VOLATILITY" in output
    assert "Iron Condor" in output
    assert "Butterfly" in output


def test_options_straddle_prompt():
    mcp = FastMCP("AEVO")
    prompts = register_options_prompts(mcp)

    output = prompts["options_straddle"](asset="BTC", expiry="28MAR25", strike="70000")
    assert "LONG STRADDLE" in output
    assert "BTC" in output
    assert "28MAR25" in output
    assert "70000" in output
    assert "Max Loss" in output
    assert "Breakeven" in output
    assert "aevo_create_order" in output


def test_options_iron_condor_prompt():
    mcp = FastMCP("AEVO")
    prompts = register_options_prompts(mcp)

    output = prompts["options_iron_condor"](
        asset="ETH",
        expiry="28MAR25",
        put_buy_strike="2500",
        put_sell_strike="2800",
        call_sell_strike="3200",
        call_buy_strike="3500",
    )
    assert "IRON CONDOR" in output
    assert "4 legs" in output
    assert "2500" in output
    assert "3500" in output
    assert "Net Credit" in output
    assert "Wing Width" in output


def test_options_butterfly_prompt():
    mcp = FastMCP("AEVO")
    prompts = register_options_prompts(mcp)

    output = prompts["options_butterfly"](
        asset="ETH",
        expiry="28MAR25",
        lower_strike="2800",
        middle_strike="3000",
        upper_strike="3200",
    )
    assert "BUTTERFLY" in output
    assert "equidistant" in output
    assert "SELL x2" in output
    assert "BUY  x1" in output
    assert "2800" in output
    assert "3000" in output
    assert "3200" in output
