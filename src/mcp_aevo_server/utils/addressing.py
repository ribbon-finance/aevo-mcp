from __future__ import annotations

from ..config import AevoMcpConfig
from ..signing import derive_address


def resolve_wallet_address(config: AevoMcpConfig) -> str:
    if config.wallet_address:
        return config.wallet_address.strip()
    if not config.wallet_private_key:
        raise RuntimeError("AEVO_WALLET_ADDRESS or AEVO_WALLET_PRIVATE_KEY is required")
    return derive_address(config.wallet_private_key)
