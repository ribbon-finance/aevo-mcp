from __future__ import annotations

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from ..client import AevoApiError
from ..config import AevoMcpConfig
from ..utils import err_response, ok_response
from ..utils.addressing import resolve_account_address, resolve_signing_key_address


def status_payload(config: AevoMcpConfig, client: Any) -> Dict[str, Any]:
    try:
        account_address = resolve_account_address(config)
        signing_key_address = resolve_signing_key_address(config)
    except RuntimeError:
        account_address = config.account_address or ""
        signing_key_address = config.signing_key_address or ""

    return {
        "environment": config.environment,
        "api_base_url": config.api_base_url,
        "account_address": account_address,
        "signing_key": signing_key_address,
        "has_signing_keys": bool(config.account_private_key and config.signing_key_private_key),
        "has_api_credentials": client.has_credentials,
        "mcp_host": config.mcp_host,
        "mcp_port": config.mcp_port,
        "mcp_path": config.mcp_path,
        "mcp_transport": config.mcp_transport,
    }


def require_api_credentials(client: Any) -> None:
    if not client.has_credentials:
        raise RuntimeError("missing AEVO_API_KEY/AEVO_API_SECRET; call register_account first")


def register_account_tools(mcp: FastMCP, client: Any, config: AevoMcpConfig) -> Dict[str, Any]:
    @mcp.tool()
    def status() -> Dict[str, Any]:
        """Return MCP runtime and AEVO identity context."""
        return ok_response(status_payload(config, client))

    @mcp.tool()
    def account() -> Dict[str, Any]:
        """Return account object for current credentials."""
        try:
            require_api_credentials(client)
            return ok_response(client.get_account())
        except (RuntimeError, AevoApiError) as exc:
            return err_response("failed to fetch account", str(exc))
        except Exception as exc:
            return err_response("failed to fetch account", str(exc))

    @mcp.tool()
    def portfolio() -> Dict[str, Any]:
        """Return portfolio for current credentials."""
        try:
            require_api_credentials(client)
            return ok_response(client.get_portfolio())
        except (RuntimeError, AevoApiError) as exc:
            return err_response("failed to fetch portfolio", str(exc))
        except Exception as exc:
            return err_response("failed to fetch portfolio", str(exc))

    @mcp.tool()
    def positions() -> Dict[str, Any]:
        """Return open positions for current credentials."""
        try:
            require_api_credentials(client)
            return ok_response(client.get_positions())
        except (RuntimeError, AevoApiError) as exc:
            return err_response("failed to fetch positions", str(exc))
        except Exception as exc:
            return err_response("failed to fetch positions", str(exc))

    return {
        "status": status,
        "account": account,
        "portfolio": portfolio,
        "positions": positions,
        "status_payload": lambda: status_payload(config, client),
        "require_api_credentials": lambda: require_api_credentials(client),
    }
