from __future__ import annotations

from types import SimpleNamespace

from mcp_aevo_server.utils import err_response, ok_response, parse_int_field, resolve_account_address, resolve_signing_key_address


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


def test_resolve_account_address_from_private_key():
    config = SimpleNamespace(account_address="", account_private_key="0x" + "1" * 64)
    address = resolve_account_address(config)
    assert address.startswith("0x")
    assert len(address) == 42


def test_resolve_account_address_from_env_value():
    config = SimpleNamespace(account_address="0x0000000000000000000000000000000000000001", account_private_key="")
    address = resolve_account_address(config)
    assert address == "0x0000000000000000000000000000000000000001"


def test_resolve_signing_key_address_missing_raises():
    config = SimpleNamespace(signing_key_address="", signing_key_private_key="")
    try:
        resolve_signing_key_address(config)
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass

