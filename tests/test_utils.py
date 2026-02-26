from __future__ import annotations

from types import SimpleNamespace

import pytest

from mcp_aevo_server.utils import err_response, ok_response, parse_int_field, pick, resolve_auth, resolve_wallet_address


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
        raise AssertionError("expected ValueError")
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
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


def test_pick_whitelists_fields():
    d = {"a": 1, "b": 2, "c": 3}
    assert pick(d, ["a", "c"]) == {"a": 1, "c": 3}


def test_pick_missing_keys():
    d = {"a": 1}
    assert pick(d, ["a", "b"]) == {"a": 1}


def test_pick_empty():
    assert pick({}, ["a"]) == {}


def test_resolve_auth_both_provided():
    result = resolve_auth(api_key="k", api_secret="s")
    assert result == ("k", "s")


def test_resolve_auth_session_fallback():
    result = resolve_auth(session_api_key="sk", session_api_secret="ss")
    assert result == ("sk", "ss")


def test_resolve_auth_none_when_empty():
    result = resolve_auth()
    assert result is None


def test_resolve_auth_partial_raises():
    with pytest.raises(RuntimeError, match="must be provided together"):
        resolve_auth(api_key="k")


def test_resolve_auth_explicit_overrides_session():
    result = resolve_auth(api_key="k", api_secret="s", session_api_key="sk", session_api_secret="ss")
    assert result == ("k", "s")
