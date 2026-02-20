from __future__ import annotations

import json
from collections.abc import Callable
from mcp.server.fastmcp import FastMCP


def register_market_resources(
    mcp: FastMCP,
    status_tool,
    market_tool,
    account_tool,
) -> dict[str, Callable]:
    @mcp.resource("aevo://status")
    def resource_status() -> str:
        return json.dumps(status_tool(), indent=2)

    @mcp.resource("aevo://markets/summary")
    def resource_markets_summary() -> str:
        return json.dumps(market_tool(), indent=2)

    @mcp.resource("aevo://account/overview")
    def resource_account_overview() -> str:
        return json.dumps(account_tool(), indent=2)

    return {
        "resource_status": resource_status,
        "resource_markets_summary": resource_markets_summary,
        "resource_account_overview": resource_account_overview,
    }
