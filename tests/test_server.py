from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from mcp_aevo_server import server


def test_build_server_registers_tools_and_components(monkeypatch):
    class FakeClient:
        def __init__(self, config):
            self.config = config
            self.has_credentials = False

        def get_markets(self, *args, **kwargs):
            return []

    class CaptureServer:
        def __init__(self, _name):
            self.tools = []
            self.prompts = []
            self.resources = []

        def tool(self, *args, **kwargs):
            def decorator(func):
                self.tools.append(func.__name__)
                return func

            return decorator

        def prompt(self, *args, **kwargs):
            def decorator(func):
                self.prompts.append(func.__name__)
                return func

            return decorator

        def resource(self, *args, **kwargs):
            def decorator(func):
                self.resources.append(args[0] if args else None)
                return func

            return decorator

        def run(self, *args, **kwargs):
            raise RuntimeError("run should not be called in this test")

    status_tool = Mock(name="status")
    account_tool = Mock(name="account")
    markets_tool = Mock(name="markets")
    funding_rate_tool = Mock(name="funding_rate")
    statistics_tool = Mock(name="statistics")

    market_tools = {
        "markets": markets_tool,
        "assets": Mock(name="assets"),
        "orderbook": Mock(name="orderbook"),
        "instrument": Mock(name="instrument"),
        "funding_rate": funding_rate_tool,
        "funding_history": Mock(name="funding_history"),
        "trade_history": Mock(name="trade_history"),
        "statistics": statistics_tool,
        "index_price": Mock(name="index_price"),
        "index_history": Mock(name="index_history"),
        "mark_history": Mock(name="mark_history"),
        "settlement_history": Mock(name="settlement_history"),
        "expiries": Mock(name="expiries"),
        "server_time": Mock(name="server_time"),
    }
    account_tools = {
        "status": status_tool,
        "account": account_tool,
        "portfolio": Mock(name="portfolio"),
        "positions": Mock(name="positions"),
        "account_trade_history": Mock(name="account_trade_history"),
        "order_history": Mock(name="order_history"),
    }
    order_tools = {
        "list_orders": Mock(name="list_orders"),
        "get_order": Mock(name="get_order"),
        "build_order": Mock(name="build_order"),
        "create_order": Mock(name="create_order"),
        "cancel_order": Mock(name="cancel_order"),
        "cancel_orders": Mock(name="cancel_orders"),
        "cancel_all": Mock(name="cancel_all"),
    }
    registration_tools = {"register_account": Mock(name="register_account", return_value={"ok": True})}

    captured = CaptureServer("AEVO Trading")

    monkeypatch.setattr(server, "AevoAPIClient", FakeClient)
    monkeypatch.setattr(server, "FastMCP", lambda name, **kwargs: captured)
    monkeypatch.setattr(server, "register_market_tools", Mock(return_value=market_tools))
    monkeypatch.setattr(server, "register_account_tools", Mock(return_value=account_tools))
    monkeypatch.setattr(server, "register_order_tools", Mock(return_value=order_tools))
    monkeypatch.setattr(server, "register_registration_tools", Mock(return_value=registration_tools))

    mock_prompt_reg = Mock(return_value={"trade_plan": Mock(name="trade_plan"), "risk_checklist": Mock(name="risk_checklist")})
    mock_resource_reg = Mock(return_value={"resource_status": Mock(name="resource_status")})
    monkeypatch.setattr(server, "register_prompts", mock_prompt_reg)
    monkeypatch.setattr(server, "register_market_resources", mock_resource_reg)

    config = SimpleNamespace(
        environment="mainnet",
        wallet_private_key="0x" + "1" * 64,
        signing_key_private_key="0x" + "2" * 64,
    )

    mcp, register_fn = server._build_server(config)

    assert mcp is captured
    assert set(captured.tools) == {"ping", "healthcheck"}
    assert mock_prompt_reg.call_count == 1
    assert mock_prompt_reg.call_args.args == (captured,)
    assert mock_resource_reg.called

    resource_kwargs = mock_resource_reg.call_args.kwargs
    assert resource_kwargs["status_tool"] is status_tool
    assert resource_kwargs["market_tool"] is markets_tool
    assert resource_kwargs["account_tool"] is account_tool
    assert resource_kwargs["funding_tool"] is funding_rate_tool
    assert resource_kwargs["statistics_tool"] is statistics_tool

    assert register_fn is registration_tools["register_account"]


def test_run_auto_register_when_disabled_returns_none():
    config = SimpleNamespace(
        auto_register=False,
        api_key="",
        api_secret="",
        wallet_private_key="",
        signing_key_private_key="",
    )
    register = Mock()

    result = server._run_auto_register(config, register)

    assert result is None
    register.assert_not_called()


def test_run_auto_register_skips_when_api_credentials_are_present():
    config = SimpleNamespace(
        auto_register=True,
        api_key="api-key",
        api_secret="api-secret",
        wallet_private_key="",
        signing_key_private_key="",
    )
    register = Mock()

    result = server._run_auto_register(config, register)

    assert result == {
        "ok": True,
        "result": "auto-register skipped because AEVO_API_KEY/AEVO_API_SECRET are already set",
    }
    register.assert_not_called()


def test_run_auto_register_fails_if_signing_keys_missing():
    config = SimpleNamespace(
        auto_register=True,
        api_key="",
        api_secret="",
        wallet_private_key="",
        signing_key_private_key="",
    )
    register = Mock()

    result = server._run_auto_register(config, register)

    assert result == {
        "ok": False,
        "error": "auto-register skipped",
        "details": "missing AEVO_WALLET_PRIVATE_KEY or AEVO_SIGNING_KEY_PRIVATE_KEY",
    }
    register.assert_not_called()


def test_run_auto_register_calls_register_function_when_ready():
    config = SimpleNamespace(
        auto_register=True,
        api_key="",
        api_secret="",
        wallet_private_key="0x" + "1" * 64,
        signing_key_private_key="0x" + "2" * 64,
    )
    register = Mock(return_value={"ok": True, "result": {"ok": True}})

    result = server._run_auto_register(config, register)

    register.assert_called_once()
    assert result == {"ok": True, "result": {"ok": True}}
