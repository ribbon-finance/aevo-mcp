from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Dict


class AevoConfigError(ValueError):
    """Raised when required AEVO MCP environment configuration is invalid."""


NETWORKS: Dict[str, Dict[str, object]] = {
    "mainnet": {
        "domain": "Aevo Mainnet",
        "chain_id": 1,
        "api_base_url": "https://api.aevo.xyz",
    },
    "testnet": {
        "domain": "Aevo Testnet",
        "chain_id": 11155111,
        "api_base_url": "https://api-testnet.aevo.xyz",
    },
}


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is not None:
        value = value.strip()
    if value == "":
        return default
    return value if value is not None else default


def _env_int(name: str, default: int) -> int:
    raw = _env(name, None)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as err:
        raise AevoConfigError(f"{name} must be an integer") from err


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name, str(default)).lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    raise AevoConfigError(f"{name} must be true|false")


@dataclass(frozen=True)
class AevoNetworkConfig:
    name: str
    chain_id: int


@dataclass(frozen=True)
class AevoMcpConfig:
    environment: str
    api_base_url: str
    wallet_address: str
    wallet_private_key: str
    signing_key_private_key: str
    api_key: str
    api_secret: str
    auto_register: bool
    request_timeout_seconds: int
    request_retries: int
    request_retry_base_ms: int
    request_id_prefix: str
    mcp_host: str
    mcp_port: int
    mcp_path: str
    mcp_transport: str

    @property
    def network(self) -> AevoNetworkConfig:
        info = NETWORKS[self.environment]
        return AevoNetworkConfig(name=info["domain"], chain_id=int(info["chain_id"]))


def load_config() -> AevoMcpConfig:
    environment = ((_env("AEVO_ENVIRONMENT") or _env("AEVO_ENV") or "mainnet") or "mainnet").lower()
    if environment not in NETWORKS:
        raise AevoConfigError(
            f"AEVO_ENVIRONMENT (or AEVO_ENV) must be one of: {', '.join(sorted(NETWORKS.keys()))}"
        )
    env_cfg = NETWORKS[environment]

    # Warn on deprecated env var names
    if _env("AEVO_ACCOUNT_ADDRESS"):
        print("[aevo-mcp] AEVO_ACCOUNT_ADDRESS is deprecated, use AEVO_WALLET_ADDRESS", file=sys.stderr)
    if _env("AEVO_ACCOUNT_PRIVATE_KEY"):
        print("[aevo-mcp] AEVO_ACCOUNT_PRIVATE_KEY is deprecated, use AEVO_WALLET_PRIVATE_KEY", file=sys.stderr)

    return AevoMcpConfig(
        environment=environment,
        api_base_url=(_env("AEVO_API_BASE_URL", env_cfg["api_base_url"]) or env_cfg["api_base_url"]).rstrip("/"),
        wallet_address=_env("AEVO_WALLET_ADDRESS") or _env("AEVO_ACCOUNT_ADDRESS", "") or "",
        wallet_private_key=_env("AEVO_WALLET_PRIVATE_KEY") or _env("AEVO_ACCOUNT_PRIVATE_KEY", "") or "",
        signing_key_private_key=_env("AEVO_SIGNING_KEY_PRIVATE_KEY", "") or "",
        api_key=_env("AEVO_API_KEY", "") or "",
        api_secret=_env("AEVO_API_SECRET", "") or "",
        auto_register=_env_bool("AEVO_AUTO_REGISTER", False),
        request_timeout_seconds=_env_int("AEVO_REQUEST_TIMEOUT_SECONDS", 12),
        request_retries=_env_int("AEVO_REQUEST_RETRIES", 3),
        request_retry_base_ms=_env_int("AEVO_REQUEST_RETRY_BASE_MS", 200),
        request_id_prefix=_env("AEVO_REQUEST_ID_PREFIX", "aevo-mcp"),
        mcp_host=_env("AEVO_MCP_HOST", "127.0.0.1") or "127.0.0.1",
        mcp_port=_env_int("AEVO_MCP_PORT", 8080),
        mcp_path=(_env("AEVO_MCP_PATH", "/mcp") or "/mcp"),
        mcp_transport=(_env("AEVO_MCP_TRANSPORT", "streamable-http") or "streamable-http").lower(),
    )
