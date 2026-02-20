from __future__ import annotations

import argparse
import json

from mcp.server.fastmcp import FastMCP

from .client import AevoAPIClient, AevoApiError
from .config import AevoConfigError, AevoMcpConfig, load_config
from .tools.account import register_account_tools
from .tools.market import register_market_tools
from .tools.order import register_order_tools
from .tools.register import register_registration_tools
from .prompts import register_prompts
from .resources import register_market_resources
from .utils import err_response, ok_response


def _run_auto_register(config: AevoMcpConfig, register_fn):
    if not config.auto_register:
        return None
    if config.api_key and config.api_secret:
        return ok_response("auto-register skipped because AEVO_API_KEY/AEVO_API_SECRET are already set")
    if not config.account_private_key or not config.signing_key_private_key:
        return err_response(
            "auto-register skipped",
            "missing AEVO_ACCOUNT_PRIVATE_KEY or AEVO_SIGNING_KEY_PRIVATE_KEY",
        )

    return register_fn()


def _build_server(config: AevoMcpConfig) -> tuple[FastMCP, object]:
    client = AevoAPIClient(config)
    mcp = FastMCP("AEVO Trading")

    market_tools = register_market_tools(mcp, client)
    account_tools = register_account_tools(mcp, client, config)
    register_order_tools(mcp, client, config)
    registration_tools = register_registration_tools(mcp, client, config)

    register_prompts(mcp)
    register_market_resources(
        mcp,
        status_tool=account_tools["status"],
        market_tool=market_tools["markets"],
        account_tool=account_tools["account"],
    )

    # keep a named local for compatibility with auto-register bootstrap
    register_fn = registration_tools["register_account"]

    # This keeps startup behavior in sync with old public surface for diagnostics and smoke flows.
    @mcp.tool()
    def ping() -> dict:
        return ok_response({"status": "ok", "transport": config.mcp_transport})

    @mcp.tool()
    def healthcheck() -> dict:
        try:
            client.get_markets(asset="", instrument_type="", use_cache=False)
            return ok_response({"api_access": "ok", "api_base_url": config.api_base_url})
        except AevoApiError as exc:
            return err_response("healthcheck failed", str(exc))
        except Exception as exc:
            return err_response("healthcheck failed", str(exc))

    return mcp, register_fn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AEVO MCP server")
    parser.add_argument("--transport", default=None, choices=["stdio", "streamable-http"], help="Transport to use")
    parser.add_argument("--host", default=None, help="Host for streamable-http")
    parser.add_argument("--port", type=int, default=None, help="Port for streamable-http")
    parser.add_argument("--path", default=None, help="Path for streamable-http")

    args = parser.parse_args()

    try:
        config = load_config()
    except AevoConfigError as exc:
        print(f"Invalid config: {exc}")
        raise SystemExit(1)

    server, register_fn = _build_server(config)
    auto = _run_auto_register(config, register_fn)
    if auto is not None:
        print(f"[aevo-mcp] auto-register: {json.dumps(auto)}")

    transport = (args.transport or config.mcp_transport).lower()
    if transport == "stdio":
        server.run(transport="stdio")
        return

    server.run(
        transport=transport,
        host=(args.host or config.mcp_host),
        port=(args.port or config.mcp_port),
        path=(args.path or config.mcp_path),
    )


if __name__ == "__main__":
    main()
