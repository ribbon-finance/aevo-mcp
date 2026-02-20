from __future__ import annotations

import json
from collections.abc import Callable
from mcp.server.fastmcp import FastMCP


def register_market_resources(
    mcp: FastMCP,
    status_tool,
    market_tool,
    account_tool,
    funding_tool=None,
    statistics_tool=None,
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

    result: dict[str, Callable] = {
        "resource_status": resource_status,
        "resource_markets_summary": resource_markets_summary,
        "resource_account_overview": resource_account_overview,
    }

    if funding_tool is not None:

        @mcp.resource("aevo://funding/snapshot")
        def resource_funding_snapshot() -> str:
            return json.dumps(funding_tool("ETH-PERP"), indent=2)

        result["resource_funding_snapshot"] = resource_funding_snapshot

    if statistics_tool is not None:

        @mcp.resource("aevo://statistics/snapshot")
        def resource_statistics_snapshot() -> str:
            return json.dumps(statistics_tool(), indent=2)

        result["resource_statistics_snapshot"] = resource_statistics_snapshot

    return result
