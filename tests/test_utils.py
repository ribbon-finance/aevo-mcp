from __future__ import annotations

from types import SimpleNamespace

from mcp_aevo_server.utils import err_response, ok_response, parse_int_field, resolve_wallet_address


def test_ok_response_payload():
    payload = ok_response({"a": 1})
    assert payload == {"ok": True, "result": {"a": 1}}


def test_err_response_payload():
    payload = err_response("bad", "reason")
    assert payload == {"ok": False, "error": "bad", "details": "reason"}


def test_parse_int_field_from_str():
    assert parse_int_field("123", "x") == 123


def test_parse_int_field_invalid():
    try:
        parse_int_field("abc", "x")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "x must be integer-like" in str(exc)


def test_resolve_wallet_address_from_private_key():
    config = SimpleNamespace(wallet_address="", wallet_private_key="0x" + "1" * 64)
    address = resolve_wallet_address(config)
    assert address.startswith("0x")
    assert len(address) == 42


def test_resolve_wallet_address_from_env_value():
    config = SimpleNamespace(wallet_address="0x0000000000000000000000000000000000000001", wallet_private_key="")
    address = resolve_wallet_address(config)
    assert address == "0x0000000000000000000000000000000000000001"


def test_resolve_wallet_address_missing_raises():
    config = SimpleNamespace(wallet_address="", wallet_private_key="")
    try:
        resolve_wallet_address(config)
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass
