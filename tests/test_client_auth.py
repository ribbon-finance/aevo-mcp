"""Test that AevoAPIClient generates HMAC-SHA256 signatures matching the Aevo SDK pattern."""

from __future__ import annotations

import hashlib
import hmac
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_aevo_server.client import AevoAPIClient


# make config for testing
def _make_config(**overrides):
    defaults = dict(
        api_base_url="https://api.aevo.xyz",
        api_key="test-api-key",
        api_secret="test-api-secret",
        request_timeout_seconds=12,
        request_retries=1,
        request_retry_base_ms=200,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _compute_expected_signature(
    api_key: str, api_secret: str, timestamp: str, method: str, path: str, body_str: str
) -> str:
    """Reproduce the SDK HMAC signing logic."""
    message = f"{api_key},{timestamp},{method},{path},{body_str}"
    return hmac.new(api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def _mock_response(status_code=200, text='{"ok": true}', json_data=None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    resp.reason_phrase = "OK"
    resp.json.return_value = json_data if json_data is not None else json.loads(text)
    return resp


@pytest.mark.asyncio
@patch("mcp_aevo_server.client.time")
async def test_hmac_headers_on_get_request(mock_time):
    mock_time.time_ns.return_value = 1700000000000000000
    mock_time.time.return_value = 1700000000.0

    config = _make_config()
    client = AevoAPIClient(config)

    mock_resp = _mock_response()
    mock_http_client = AsyncMock(spec=httpx.AsyncClient)
    mock_http_client.request = AsyncMock(return_value=mock_resp)
    client._client = mock_http_client

    await client._request("GET", "/account")

    call_kwargs = mock_http_client.request.call_args
    headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})

    assert headers["AEVO-KEY"] == "test-api-key"
    assert headers["AEVO-TIMESTAMP"] == "1700000000000000000"
    assert "AEVO-SIGNATURE" in headers
    assert "AEVO-SECRET" not in headers

    expected_sig = _compute_expected_signature(
        "test-api-key",
        "test-api-secret",
        "1700000000000000000",
        "GET",
        "/account",
        "",
    )
    assert headers["AEVO-SIGNATURE"] == expected_sig
    await client.close()


@pytest.mark.asyncio
@patch("mcp_aevo_server.client.time")
async def test_hmac_headers_on_post_with_body(mock_time):
    mock_time.time_ns.return_value = 1700000000000000000
    mock_time.time.return_value = 1700000000.0

    config = _make_config()
    client = AevoAPIClient(config)

    mock_resp = _mock_response(text='{"id": "order-1"}', json_data={"id": "order-1"})
    mock_http_client = AsyncMock(spec=httpx.AsyncClient)
    mock_http_client.request = AsyncMock(return_value=mock_resp)
    client._client = mock_http_client

    body = {"maker": "0xabc", "is_buy": True, "amount": "10"}
    await client._request("POST", "/orders", json=body)

    call_kwargs = mock_http_client.request.call_args
    headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})

    expected_body_str = json.dumps(body, separators=(",", ":"))
    expected_sig = _compute_expected_signature(
        "test-api-key",
        "test-api-secret",
        "1700000000000000000",
        "POST",
        "/orders",
        expected_body_str,
    )
    assert headers["AEVO-SIGNATURE"] == expected_sig
    await client.close()


@pytest.mark.asyncio
async def test_no_auth_headers_when_credentials_missing():
    config = _make_config(api_key="", api_secret="")
    client = AevoAPIClient(config)

    mock_resp = _mock_response(text="[]", json_data=[])
    mock_http_client = AsyncMock(spec=httpx.AsyncClient)
    mock_http_client.request = AsyncMock(return_value=mock_resp)
    client._client = mock_http_client

    await client._request("GET", "/markets")

    call_kwargs = mock_http_client.request.call_args
    headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})

    assert "AEVO-KEY" not in headers
    assert "AEVO-SECRET" not in headers
    assert "AEVO-SIGNATURE" not in headers
    assert "AEVO-TIMESTAMP" not in headers
    await client.close()


@pytest.mark.asyncio
async def test_no_auth_headers_when_headers_explicitly_overridden():
    """When headers={} is passed (like register()), no HMAC should be injected."""
    config = _make_config()
    client = AevoAPIClient(config)

    mock_resp = _mock_response()
    mock_http_client = AsyncMock(spec=httpx.AsyncClient)
    mock_http_client.request = AsyncMock(return_value=mock_resp)
    client._client = mock_http_client

    await client._request("POST", "/register", json={"account": "0xabc"}, headers={})

    call_kwargs = mock_http_client.request.call_args
    headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})

    assert "AEVO-KEY" not in headers
    assert "AEVO-SIGNATURE" not in headers
    assert "AEVO-TIMESTAMP" not in headers
    await client.close()


def test_hmac_signature_matches_sdk_format():
    """Verify the HMAC computation matches the SDK's exact format:
    message = f"{api_key},{timestamp},{method},{path},{body}"
    signature = hmac.new(api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    """
    api_key = "my-key"
    api_secret = "my-secret"
    timestamp = "1700000000000000000"
    method = "POST"
    path = "/orders"
    body = '{"maker":"0xabc"}'

    message = f"{api_key},{timestamp},{method},{path},{body}"
    sig = hmac.new(api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    assert len(sig) == 64  # SHA-256 hex digest is 64 hex chars
    # HMAC != plain SHA-256 hash — verify they differ
    plain_hash = hashlib.sha256(message.encode()).hexdigest()
    assert sig != plain_hash


@pytest.mark.asyncio
@patch("mcp_aevo_server.client.time")
async def test_hmac_headers_on_get_request_with_auth_override(mock_time):
    mock_time.time_ns.return_value = 1700000000000000000
    mock_time.time.return_value = 1700000000.0

    config = _make_config(api_key="", api_secret="")
    client = AevoAPIClient(config)

    mock_resp = _mock_response()
    mock_http_client = AsyncMock(spec=httpx.AsyncClient)
    mock_http_client.request = AsyncMock(return_value=mock_resp)
    client._client = mock_http_client

    await client._request("GET", "/account", auth=("user-key", "user-secret"))

    call_kwargs = mock_http_client.request.call_args
    headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})

    assert headers["AEVO-KEY"] == "user-key"
    assert headers["AEVO-TIMESTAMP"] == "1700000000000000000"
    expected_sig = _compute_expected_signature(
        "user-key",
        "user-secret",
        "1700000000000000000",
        "GET",
        "/account",
        "",
    )
    assert headers["AEVO-SIGNATURE"] == expected_sig
    await client.close()
