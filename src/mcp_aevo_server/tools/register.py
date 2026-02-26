from __future__ import annotations

from dataclasses import is_dataclass, replace
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from ..config import AevoMcpConfig
from ..session_auth import SessionAuthStore
from ..signing import derive_address, sign_register_payload
from ..utils.addressing import resolve_wallet_address
from ..utils.validation import parse_int_field


def _max_expiry_value() -> str:
    return str(2**256 - 1)


def register_registration_tools(
    mcp: FastMCP, client: Any, config: AevoMcpConfig, auth_store: SessionAuthStore | None = None
) -> dict[str, Any]:
    def _config_with_overrides(**overrides: Any) -> Any:
        effective: dict[str, Any] = {}
        for key, value in overrides.items():
            if isinstance(value, str):
                normalized = value.strip()
                if normalized:
                    effective[key] = normalized
            elif value is not None:
                effective[key] = value
        if not effective:
            return config
        if is_dataclass(config):
            return replace(config, **effective)
        merged = dict(vars(config))
        merged.update(effective)
        return type(config)(**merged)

    def _require_signing_keys(runtime_config: Any) -> None:
        if not runtime_config.wallet_private_key:
            raise RuntimeError("AEVO_WALLET_PRIVATE_KEY is required")
        if not runtime_config.signing_key_private_key:
            raise RuntimeError("AEVO_SIGNING_KEY_PRIVATE_KEY is required")

    @mcp.tool(
        name="aevo_register_account",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True
        ),
    )
    async def register_account(
        key_expiry: str = "",
        no_api_key: bool = False,
        referral_code: str = "",
        wallet_address: str = "",
        store_credentials: bool = True,
        ctx: Context | None = None,
    ) -> dict:
        """Register signing key on AEVO and optionally obtain API credentials.

        Requires wallet and signing key private keys from env vars or session auth.
        On success, API credentials are automatically stored for subsequent calls.

        Args:
            key_expiry: Signing key expiry as integer string. Defaults to max uint256.
            no_api_key: If True, skip API key generation.
            referral_code: Optional referral code.
            wallet_address: Optional wallet address override.
            store_credentials: If True (default), store returned API credentials.
        """
        session_creds = auth_store.get_for_context(ctx) if auth_store else None
        runtime_config = _config_with_overrides(
            wallet_address=wallet_address or (session_creds.wallet_address if session_creds else ""),
            wallet_private_key=session_creds.wallet_private_key if session_creds else "",
            signing_key_private_key=session_creds.signing_key_private_key if session_creds else "",
        )
        _require_signing_keys(runtime_config)
        account_address = resolve_wallet_address(runtime_config)
        signing_key_address = derive_address(runtime_config.signing_key_private_key)

        expiry = _max_expiry_value()
        if key_expiry:
            expiry = str(parse_int_field(key_expiry, "key_expiry"))

        signed = sign_register_payload(
            network=runtime_config.network,
            account_address=account_address,
            account_private_key=runtime_config.wallet_private_key,
            signing_key_address=signing_key_address,
            signing_key_private_key=runtime_config.signing_key_private_key,
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

        response = await client.register(payload)
        response_data = response if isinstance(response, dict) else {"raw": response}
        api_key = str(response_data.get("api_key", "") or "")
        api_secret = str(response_data.get("api_secret", "") or "")
        if store_credentials and api_key and api_secret:
            if auth_store and ctx is not None:
                auth_store.upsert_for_context(
                    ctx,
                    api_key=api_key,
                    api_secret=api_secret,
                    wallet_address=account_address,
                    wallet_private_key=runtime_config.wallet_private_key,
                    signing_key_private_key=runtime_config.signing_key_private_key,
                )
            else:
                client.set_credentials(api_key, api_secret)
            response_data["stored"] = True
        else:
            response_data["stored"] = False
        return response_data

    return {"register_account": register_account}
