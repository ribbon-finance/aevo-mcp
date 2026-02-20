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

    assert "Trade plan" in prompts["trade_plan"]("BTC-USDC", "buy", "1", "50000")
    assert "Pre-trade checklist" in prompts["risk_checklist"]()


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
