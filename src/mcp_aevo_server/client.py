from __future__ import annotations

import asyncio
import hashlib
import hmac
import json as json_mod
import random
import sys
import time
from typing import Any

import httpx

from .config import AevoMcpConfig
from .utils.rate_limit import RateLimiter

AuthPair = tuple[str, str]


class AevoApiError(RuntimeError):
    def __init__(self, status_code: int, message: str, response: str | None = None):
        self.status_code = status_code
        self.response = response
        if message:
            message = f"[HTTP {status_code}] {message}"
        super().__init__(message)


class AevoAPIClient:
    def __init__(self, config: AevoMcpConfig):
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._api_key = config.api_key
        self._api_secret = config.api_secret
        self._market_cache: tuple[float, list[dict[str, Any]]] = (0.0, [])
        self._rate_limiter = RateLimiter(rate=30.0)

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.request_timeout_seconds)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def base_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @property
    def has_credentials(self) -> bool:
        return bool(self._api_key and self._api_secret)

    def set_credentials(self, api_key: str, api_secret: str) -> None:
        self._api_key = (api_key or "").strip()
        self._api_secret = (api_secret or "").strip()

    def clear_credentials(self) -> None:
        self._api_key = ""
        self._api_secret = ""

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
        auth: AuthPair | None = None,
    ) -> Any:
        await self._rate_limiter.acquire()
        client = await self._ensure_client()
        url = f"{self.config.api_base_url.rstrip('/')}/{path.lstrip('/')}"
        merged_headers = self.base_headers.copy()
        auth_key, auth_secret = auth or (self._api_key, self._api_secret)
        auth_key = (auth_key or "").strip()
        auth_secret = (auth_secret or "").strip()
        if headers is not None:
            merged_headers.update(headers)
        else:
            if auth_key and auth_secret:
                timestamp = str(time.time_ns())
                body_str = json_mod.dumps(json, separators=(",", ":")) if json else ""
                message = f"{auth_key},{timestamp},{method.upper()},{path},{body_str}"
                signature = hmac.new(auth_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
                merged_headers["AEVO-KEY"] = auth_key
                merged_headers["AEVO-TIMESTAMP"] = timestamp
                merged_headers["AEVO-SIGNATURE"] = signature

        # Log order mutations to stderr
        is_mutation = method.upper() in ("POST", "DELETE") and "order" in path.lower()
        if is_mutation:
            print(f"[aevo-mcp] {method.upper()} {path}", file=sys.stderr)

        last_error = None
        for attempt in range(1, self.config.request_retries + 1):
            try:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=merged_headers,
                )
            except httpx.HTTPError as err:
                last_error = err
                if attempt >= self.config.request_retries:
                    raise AevoApiError(0, f"network error: {err}") from err
            else:
                last_error = None
                if response.status_code >= 500 and attempt < self.config.request_retries:
                    # Jittered backoff
                    base_wait = 0.001 * (self.config.request_retry_base_ms * attempt)
                    jitter = base_wait * (0.5 + random.random())
                    await asyncio.sleep(jitter)
                    continue
                if response.status_code >= 400:
                    try:
                        body = response.text
                        payload = response.json()
                        err = payload.get("error") if isinstance(payload, dict) else None
                    except Exception:
                        body = response.text
                        err = None
                    message = err or response.reason_phrase or "unknown error"
                    raise AevoApiError(response.status_code, message, response=body)

                text = response.text or ""
                if not text:
                    return {}
                try:
                    return response.json()
                except ValueError as err:
                    raise AevoApiError(response.status_code, f"invalid JSON response: {err}") from err

            # Jittered backoff for network errors
            base_wait = 0.001 * (self.config.request_retry_base_ms * attempt)
            jitter = base_wait * (0.5 + random.random())
            await asyncio.sleep(jitter)

        if last_error is not None:
            raise AevoApiError(0, f"request retries exhausted: {last_error}") from last_error
        raise AevoApiError(0, "unexpected request state")

    async def get_markets(
        self, *, asset: str = "", instrument_type: str = "", use_cache: bool = True
    ) -> list[dict[str, Any]]:
        is_filtered = bool(asset or instrument_type)

        if use_cache and not is_filtered:
            now = time.time()
            cached_at, cached_markets = self._market_cache
            if now - cached_at < 20 and cached_markets:
                return cached_markets

        params = {}
        if asset:
            params["asset"] = asset
        if instrument_type:
            params["instrument_type"] = instrument_type

        response = await self._request("GET", "/markets", params=params)
        markets = response if isinstance(response, list) else response.get("data", response)
        markets_list = list(markets)
        if not is_filtered:
            self._market_cache = (time.time(), markets_list)
        return markets_list

    async def resolve_instrument_id(self, instrument_name: str) -> str | None:
        normalized = (instrument_name or "").strip()
        if normalized.isdigit():
            return normalized

        markets = await self.get_markets()
        direct = {str(item.get("instrument_name")): item for item in markets}
        direct_match = direct.get(normalized)
        if direct_match:
            return str(direct_match.get("instrument_id"))

        lowered = normalized.lower()
        for item in markets:
            candidate = str(item.get("instrument_name", "")).strip().lower()
            if candidate == lowered:
                return str(item.get("instrument_id"))
        return None

    async def get_assets(self) -> Any:
        return await self._request("GET", "/assets")

    async def get_orderbook(self, instrument_name: str) -> Any:
        return await self._request("GET", "/orderbook", params={"instrument_name": instrument_name})

    async def get_instrument(self, instrument_name: str) -> Any:
        return await self._request("GET", f"/instrument/{instrument_name}")

    async def update_leverage(self, instrument_id: int, leverage: int, auth: AuthPair | None = None) -> Any:
        return await self._request(
            "POST",
            "/account/leverage",
            json={"instrument": instrument_id, "leverage": leverage},
            auth=auth,
        )

    async def get_account(self, auth: AuthPair | None = None) -> Any:
        return await self._request("GET", "/account", auth=auth)

    async def get_positions(self, auth: AuthPair | None = None) -> Any:
        return await self._request("GET", "/positions", auth=auth)

    async def get_portfolio(self, auth: AuthPair | None = None) -> Any:
        return await self._request("GET", "/portfolio", auth=auth)

    async def get_orders(self, auth: AuthPair | None = None) -> Any:
        return await self._request("GET", "/orders", auth=auth)

    async def get_order(self, order_id: str, auth: AuthPair | None = None) -> Any:
        return await self._request("GET", f"/orders/{order_id}", auth=auth)

    async def create_order(self, payload: dict[str, Any], auth: AuthPair | None = None) -> Any:
        return await self._request("POST", "/orders", json=payload, auth=auth)

    async def cancel_order(self, order_id: str, auth: AuthPair | None = None) -> Any:
        return await self._request("DELETE", f"/orders/{order_id}", auth=auth)

    async def cancel_all_orders(
        self,
        instrument_type: str | None = None,
        asset: str | None = None,
        auth: AuthPair | None = None,
    ) -> Any:
        body: dict[str, Any] = {}
        if instrument_type:
            body["instrument_type"] = instrument_type
        if asset:
            body["asset"] = asset
        return await self._request("DELETE", "/orders-all", json=body or None, auth=auth)

    async def cancel_orders(
        self, order_ids: list[str], instrument_type: str | None = None, auth: AuthPair | None = None
    ) -> Any:
        body: dict[str, Any] = {"order_ids": order_ids}
        if instrument_type:
            body["instrument_type"] = instrument_type
        return await self._request("DELETE", "/orders", json=body, auth=auth)

    # -- Public market data --

    async def get_funding(self, instrument_name: str) -> Any:
        return await self._request("GET", "/funding", params={"instrument_name": instrument_name})

    async def get_funding_history(
        self,
        instrument_name: str,
        start_time: str = "",
        end_time: str = "",
        limit: str = "",
        offset: str = "",
    ) -> Any:
        params: dict[str, str] = {"instrument_name": instrument_name}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        return await self._request("GET", "/funding-history", params=params)

    async def get_trade_history_public(self, instrument_name: str) -> Any:
        return await self._request("GET", f"/instrument/{instrument_name}/trade-history")

    async def get_statistics(self) -> Any:
        return await self._request("GET", "/statistics")

    async def get_index(self, asset: str) -> Any:
        return await self._request("GET", "/index", params={"asset": asset})

    async def get_index_history(
        self,
        asset: str,
        resolution: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: str = "",
    ) -> Any:
        params: dict[str, str] = {"asset": asset}
        if resolution:
            params["resolution"] = resolution
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if limit:
            params["limit"] = limit
        return await self._request("GET", "/index-history", params=params)

    async def get_mark_history(
        self,
        instrument_name: str,
        resolution: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: str = "",
    ) -> Any:
        params: dict[str, str] = {"instrument_name": instrument_name}
        if resolution:
            params["resolution"] = resolution
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if limit:
            params["limit"] = limit
        return await self._request("GET", "/mark-history", params=params)

    async def get_settlement_history(
        self,
        asset: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: str = "",
    ) -> Any:
        params: dict[str, str] = {}
        if asset:
            params["asset"] = asset
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if limit:
            params["limit"] = limit
        return await self._request("GET", "/settlement-history", params=params)

    async def get_expiries(self, asset: str) -> Any:
        return await self._request("GET", "/expiries", params={"asset": asset})

    async def get_time(self) -> Any:
        return await self._request("GET", "/time")

    # -- Private (auth-gated) --

    async def get_account_trade_history(
        self,
        start_time: str = "",
        end_time: str = "",
        limit: str = "",
        offset: str = "",
        trade_types: str = "",
        instrument_name: str = "",
        instrument_type: str = "",
        asset: str = "",
        auth: AuthPair | None = None,
    ) -> Any:
        params: dict[str, str] = {}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        if trade_types:
            params["trade_types"] = trade_types
        if instrument_name:
            params["instrument_name"] = instrument_name
        if instrument_type:
            params["instrument_type"] = instrument_type
        if asset:
            params["asset"] = asset
        return await self._request("GET", "/trade-history", params=params, auth=auth)

    async def get_order_history(
        self,
        start_time: str = "",
        end_time: str = "",
        limit: str = "",
        offset: str = "",
        instrument_name: str = "",
        instrument_type: str = "",
        asset: str = "",
        auth: AuthPair | None = None,
    ) -> Any:
        params: dict[str, str] = {}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        if instrument_name:
            params["instrument_name"] = instrument_name
        if instrument_type:
            params["instrument_type"] = instrument_type
        if asset:
            params["asset"] = asset
        return await self._request("GET", "/order-history", params=params, auth=auth)

    async def register(self, payload: dict[str, Any]) -> Any:
        return await self._request("POST", "/register", json=payload, headers={})
