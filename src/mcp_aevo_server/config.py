from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict


class AevoConfigError(ValueError):
    """Raised when required AEVO MCP environment configuration is invalid."""


NETWORKS: Dict[str, Dict[str, object]] = {
    "mainnet": {
        "domain": "Aevo Mainnet",
        "chain_id": 1,
    },
    "testnet": {
        "domain": "Aevo Testnet",
        "chain_id": 11155111,
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
    ws_url: str
    account_address: str
    account_private_key: str
    signing_key_address: str
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
    environment = (_env("AEVO_ENVIRONMENT", "mainnet") or "mainnet").lower()
    if environment not in NETWORKS:
        raise AevoConfigError(
            f"AEVO_ENVIRONMENT must be one of: {', '.join(sorted(NETWORKS.keys()))}"
        )

    return AevoMcpConfig(
        environment=environment,
        api_base_url=(_env("AEVO_API_BASE_URL", "https://api.aevo.xyz") or "https://api.aevo.xyz").rstrip(
            "/"
        ),
        ws_url=_env("AEVO_WS_URL", "wss://ws.aevo.xyz/ws") or "wss://ws.aevo.xyz/ws",
        account_address=_env("AEVO_ACCOUNT_ADDRESS", "") or "",
        account_private_key=_env("AEVO_ACCOUNT_PRIVATE_KEY", "") or "",
        signing_key_address=_env("AEVO_SIGNING_KEY", "") or "",
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
