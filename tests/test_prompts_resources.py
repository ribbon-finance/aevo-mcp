from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from mcp_aevo_server.prompts import register_prompts
from mcp_aevo_server.resources import register_market_resources


def test_prompts_can_be_registered_and_return_text():
    mcp = FastMCP("AEVO")
    prompts = register_prompts(mcp)

    assert "trade_plan" in prompts
    assert "risk_checklist" in prompts
    assert "cancel_plan" in prompts
    assert "onboarding_plan" in prompts
    assert "market_analysis" in prompts

    trade_output = prompts["trade_plan"]("BTC-USDC", "buy", "1", "50000", time_in_force="ioc", post_only=True, reduce_only=False)
    assert "AEVO TRADE PLAN" in trade_output
    assert "Symbol: BTC-USDC" in trade_output
    assert "Side: buy" in trade_output
    assert "Time in force: IOC" in trade_output
    assert "Post-only: True" in trade_output
    assert "Reduce-only: False" in trade_output
    assert "2) Snapshot orderbook + account + positions." in trade_output
    assert "Pre-trade checklist" in prompts["risk_checklist"]()


def test_cancel_plan_prompt_is_specific():
    mcp = FastMCP("AEVO")
    prompts = register_prompts(mcp)

    no_id = prompts["cancel_plan"]()
    with_id = prompts["cancel_plan"]("order-123")

    assert "Order id: N/A" in no_id
    assert "Order id: order-123" in with_id
    assert "1) If order id known, call `cancel_order(order_id)`." in no_id
    assert "3) For batch operations use `cancel_orders` or `cancel_all`." in no_id


def test_onboarding_plan_prompt_contains_bootstrap_flow():
    mcp = FastMCP("AEVO")
    prompts = register_prompts(mcp)

    plan = prompts["onboarding_plan"]()
    assert "AEVO AGENT ONBOARDING" in plan
    assert "Fill required key fields" in plan
    assert "Run `status` to confirm identities and transport." in plan
    assert "Inspect `assets` and `markets`." in plan


def test_market_analysis_prompt():
    mcp = FastMCP("AEVO")
    prompts = register_prompts(mcp)

    output = prompts["market_analysis"]()
    assert "AEVO MARKET ANALYSIS" in output
    assert "Symbol: ETH-PERP" in output
    assert "Asset: ETH" in output
    assert "index_price" in output
    assert "funding_rate" in output
    assert "funding_history" in output
    assert "statistics" in output
    assert "trade_history" in output
    assert "mark_history" in output

    custom = prompts["market_analysis"](symbol="BTC-PERP", asset="BTC")
    assert "Symbol: BTC-PERP" in custom
    assert "Asset: BTC" in custom


def test_resources_can_be_registered_and_serialized():
    mcp = FastMCP("AEVO")

    def status_tool():
        return {"ok": True, "result": {"environment": "mainnet"}}

    def market_tool():
        return {"ok": True, "result": [{"instrument_name": "BTC-USDC"}]}

    def account_tool():
        return {"ok": True, "result": {"account": "ok"}}

    resources = register_market_resources(mcp, status_tool=status_tool, market_tool=market_tool, account_tool=account_tool)

    status = json.loads(resources["resource_status"]())
    markets = json.loads(resources["resource_markets_summary"]())
    account = json.loads(resources["resource_account_overview"]())

    assert status == {"ok": True, "result": {"environment": "mainnet"}}
    assert markets == {"ok": True, "result": [{"instrument_name": "BTC-USDC"}]}
    assert account == {"ok": True, "result": {"account": "ok"}}


def test_funding_resource():
    mcp = FastMCP("AEVO")

    calls = []

    def funding_tool(instrument_name):
        calls.append(instrument_name)
        return {"ok": True, "result": {"funding_rate": "0.0001"}}

    resources = register_market_resources(
        mcp,
        status_tool=lambda: {},
        market_tool=lambda: {},
        account_tool=lambda: {},
        funding_tool=funding_tool,
    )

    result = json.loads(resources["resource_funding_snapshot"]())
    assert result["result"]["funding_rate"] == "0.0001"
    assert calls == ["ETH-PERP"]


def test_statistics_resource():
    mcp = FastMCP("AEVO")

    def statistics_tool():
        return {"ok": True, "result": {"daily_volume": "1000000"}}

    resources = register_market_resources(
        mcp,
        status_tool=lambda: {},
        market_tool=lambda: {},
        account_tool=lambda: {},
        statistics_tool=statistics_tool,
    )

    result = json.loads(resources["resource_statistics_snapshot"]())
    assert result["result"]["daily_volume"] == "1000000"


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
