from __future__ import annotations

import hashlib
import hmac
import json as json_mod
import time
from typing import Any, Dict, List, Optional

import requests

from .config import AevoMcpConfig


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
        self._session = requests.Session()
        self._api_key = config.api_key
        self._api_secret = config.api_secret
        self._market_cache: tuple[float, List[Dict[str, Any]]] = (0.0, [])

    @property
    def base_headers(self) -> Dict[str, str]:
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

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Dict[str, str] | None = None,
        json: Dict[str, Any] | list[Any] | None = None,
        headers: Dict[str, str] | None = None,
    ) -> Any:
        url = f"{self.config.api_base_url.rstrip('/')}/{path.lstrip('/')}"
        merged_headers = self.base_headers.copy()
        if headers is not None:
            merged_headers.update(headers)
        else:
            if self._api_key and self._api_secret:
                timestamp = str(time.time_ns())
                body_str = json_mod.dumps(json) if json else ""
                message = f"{self._api_key},{timestamp},{method.upper()},{path},{body_str}"
                signature = hmac.new(
                    self._api_secret.encode(), message.encode(), hashlib.sha256
                ).hexdigest()
                merged_headers["AEVO-KEY"] = self._api_key
                merged_headers["AEVO-TIMESTAMP"] = timestamp
                merged_headers["AEVO-SIGNATURE"] = signature

        last_error = None
        for attempt in range(1, self.config.request_retries + 1):
            try:
                response = self._session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=merged_headers,
                    timeout=self.config.request_timeout_seconds,
                )
            except requests.RequestException as err:
                last_error = err
                if attempt >= self.config.request_retries:
                    raise AevoApiError(0, f"network error: {err}") from err
            else:
                last_error = None
                if response.status_code >= 500 and attempt < self.config.request_retries:
                    wait = 0.001 * (self.config.request_retry_base_ms * attempt)
                    time.sleep(wait)
                    continue
                if response.status_code >= 400:
                    try:
                        body = response.text
                        payload = response.json()
                        err = payload.get("error") if isinstance(payload, dict) else None
                    except Exception:
                        body = response.text
                        err = None
                    message = err or response.reason or "unknown error"
                    raise AevoApiError(response.status_code, message, response=body)

                text = response.text or ""
                if not text:
                    return {}
                try:
                    return response.json()
                except ValueError as err:
                    raise AevoApiError(response.status_code, f"invalid JSON response: {err}") from err

            wait = 0.001 * (self.config.request_retry_base_ms * attempt)
            time.sleep(wait)

        if last_error is not None:
            raise AevoApiError(0, f"request retries exhausted: {last_error}") from last_error
        raise AevoApiError(0, "unexpected request state")

    def get_markets(self, *, asset: str = "", instrument_type: str = "", use_cache: bool = True) -> List[Dict[str, Any]]:
        now = time.time()
        cached_at, cached_markets = self._market_cache
        if use_cache and now - cached_at < 20 and cached_markets:
            return cached_markets

        params = {}
        if asset:
            params["asset"] = asset
        if instrument_type:
            params["instrument_type"] = instrument_type

        response = self._request("GET", "/markets", params=params)
        markets = response if isinstance(response, list) else response.get("data", response)
        markets_list = list(markets)
        self._market_cache = (now, markets_list)
        return markets_list

    def resolve_instrument_id(self, instrument_name: str) -> str | None:
        normalized = (instrument_name or "").strip()
        if normalized.isdigit():
            return normalized

        markets = self.get_markets()
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

    def get_assets(self) -> Any:
        return self._request("GET", "/assets")

    def get_orderbook(self, instrument_name: str) -> Any:
        return self._request("GET", "/orderbook", params={"instrument_name": instrument_name})

    def get_instrument(self, instrument_name: str) -> Any:
        return self._request("GET", f"/instrument/{instrument_name}")

    def get_account(self) -> Any:
        return self._request("GET", "/account")

    def get_positions(self) -> Any:
        return self._request("GET", "/positions")

    def get_portfolio(self) -> Any:
        return self._request("GET", "/portfolio")

    def get_orders(self) -> Any:
        return self._request("GET", "/orders")

    def get_order(self, order_id: str) -> Any:
        return self._request("GET", f"/orders/{order_id}")

    def create_order(self, payload: Dict[str, Any]) -> Any:
        return self._request("POST", "/orders", json=payload)

    def cancel_order(self, order_id: str) -> Any:
        return self._request("DELETE", f"/orders/{order_id}")

    def cancel_all_orders(self, instrument_type: str | None = None, asset: str | None = None) -> Any:
        body: Dict[str, Any] = {}
        if instrument_type:
            body["instrument_type"] = instrument_type
        if asset:
            body["asset"] = asset
        return self._request("DELETE", "/orders-all", json=body or {})

    def cancel_orders(self, order_ids: List[str], instrument_type: str | None = None) -> Any:
        body: Dict[str, Any] = {"order_ids": order_ids}
        if instrument_type:
            body["instrument_type"] = instrument_type
        return self._request("DELETE", "/orders", json=body)

    # ── Public market data ──────────────────────────────────────────

    def get_funding(self, instrument_name: str) -> Any:
        return self._request("GET", "/funding", params={"instrument_name": instrument_name})

    def get_funding_history(
        self,
        instrument_name: str,
        start_time: str = "",
        end_time: str = "",
        limit: str = "",
        offset: str = "",
    ) -> Any:
        params: Dict[str, str] = {"instrument_name": instrument_name}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        return self._request("GET", "/funding-history", params=params)

    def get_trade_history_public(self, instrument_name: str) -> Any:
        return self._request("GET", f"/instrument/{instrument_name}/trade-history")

    def get_statistics(self) -> Any:
        return self._request("GET", "/statistics")

    def get_index(self, asset: str) -> Any:
        return self._request("GET", "/index", params={"asset": asset})

    def get_index_history(
        self,
        asset: str,
        resolution: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: str = "",
    ) -> Any:
        params: Dict[str, str] = {"asset": asset}
        if resolution:
            params["resolution"] = resolution
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if limit:
            params["limit"] = limit
        return self._request("GET", "/index-history", params=params)

    def get_mark_history(
        self,
        instrument_name: str,
        resolution: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: str = "",
    ) -> Any:
        params: Dict[str, str] = {"instrument_name": instrument_name}
        if resolution:
            params["resolution"] = resolution
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if limit:
            params["limit"] = limit
        return self._request("GET", "/mark-history", params=params)

    def get_settlement_history(
        self,
        asset: str = "",
        start_time: str = "",
        end_time: str = "",
        limit: str = "",
    ) -> Any:
        params: Dict[str, str] = {}
        if asset:
            params["asset"] = asset
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if limit:
            params["limit"] = limit
        return self._request("GET", "/settlement-history", params=params)

    def get_expiries(self, asset: str) -> Any:
        return self._request("GET", "/expiries", params={"asset": asset})

    def get_time(self) -> Any:
        return self._request("GET", "/time")

    # ── Private (auth-gated) ──────────────────────────────────────

    def get_account_trade_history(
        self,
        start_time: str = "",
        end_time: str = "",
        limit: str = "",
        offset: str = "",
        trade_types: str = "",
        instrument_name: str = "",
        instrument_type: str = "",
        asset: str = "",
    ) -> Any:
        params: Dict[str, str] = {}
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
        return self._request("GET", "/trade-history", params=params)

    def get_order_history(
        self,
        start_time: str = "",
        end_time: str = "",
        limit: str = "",
        offset: str = "",
        instrument_name: str = "",
        instrument_type: str = "",
        asset: str = "",
    ) -> Any:
        params: Dict[str, str] = {}
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
        return self._request("GET", "/order-history", params=params)

    def register(self, payload: Dict[str, Any]) -> Any:
        return self._request("POST", "/register", json=payload, headers={})
