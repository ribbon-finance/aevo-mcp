from __future__ import annotations

from ..config import AevoMcpConfig
from ..signing import derive_address


def resolve_account_address(config: AevoMcpConfig) -> str:
    if config.account_address:
        return config.account_address.strip()
    if not config.account_private_key:
        raise RuntimeError("AEVO_ACCOUNT_ADDRESS or AEVO_ACCOUNT_PRIVATE_KEY is required")
    return derive_address(config.account_private_key)


def resolve_signing_key_address(config: AevoMcpConfig) -> str:
    if config.signing_key_address:
        return config.signing_key_address.strip()
    if not config.signing_key_private_key:
        raise RuntimeError("AEVO_SIGNING_KEY or AEVO_SIGNING_KEY_PRIVATE_KEY is required")
    return derive_address(config.signing_key_private_key)
