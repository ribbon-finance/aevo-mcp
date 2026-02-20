from __future__ import annotations

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from ..client import AevoApiError
from ..config import AevoMcpConfig
from ..signing import sign_register_payload
from ..utils import err_response, ok_response, parse_int_field
from ..utils.addressing import resolve_account_address, resolve_signing_key_address


def _max_expiry_value() -> str:
    return str(2**256 - 1)


def register_registration_tools(mcp: FastMCP, client: Any, config: AevoMcpConfig) -> Dict[str, Any]:
    def _require_signing_keys() -> None:
        if not config.account_private_key:
            raise RuntimeError("AEVO_ACCOUNT_PRIVATE_KEY is required")
        if not config.signing_key_private_key:
            raise RuntimeError("AEVO_SIGNING_KEY_PRIVATE_KEY is required")

    @mcp.tool()
    def register_account(
        key_expiry: str = "",
        no_api_key: bool = False,
        referral_code: str = "",
    ) -> Dict[str, Any]:
        """Register signing key and optionally API credentials."""
        try:
            _require_signing_keys()
            account_address = resolve_account_address(config)
            signing_key_address = resolve_signing_key_address(config)

            expiry = _max_expiry_value()
            if key_expiry:
                expiry = str(parse_int_field(key_expiry, "key_expiry"))

            signed = sign_register_payload(
                network=config.network,
                account_address=account_address,
                account_private_key=config.account_private_key,
                signing_key_address=signing_key_address,
                signing_key_private_key=config.signing_key_private_key,
                expiry=expiry,
            )

            payload = {
                "account": account_address,
                "signing_key": signing_key_address,
                "expiry": str(expiry),
                "account_signature": signed["account_signature"],
                "signing_key_signature": signed["signing_key_signature"],
                "no_api_key": no_api_key,
            }
            if referral_code:
                payload["referral_code"] = referral_code

            response = client.register(payload)
            response_data = response if isinstance(response, dict) else {"raw": response}
            api_key = str(response_data.get("api_key", "") or "")
            api_secret = str(response_data.get("api_secret", "") or "")
            if api_key and api_secret:
                client.set_credentials(api_key, api_secret)
                response_data["stored"] = True
            return ok_response(response_data)
        except (RuntimeError, ValueError, AevoApiError) as exc:
            return err_response("register_account failed", str(exc))
        except Exception as exc:
            return err_response("register_account failed", str(exc))

    return {"register_account": register_account}
