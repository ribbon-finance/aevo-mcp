# AEVO MCP Server

A Model Context Protocol server for interacting with AEVO trading APIs.

## Features

- Register signing key and request API key/secret via EIP-712 payloads.
- Read account data: `account`, `portfolio`, `positions`, `markets`, `assets`, `orderbook`, `instrument`.
- Build and submit signed orders (`build_order`, `create_order`).
- Cancel and inspect open orders (`list_orders`, `get_order`, `cancel_order`, `cancel_orders`, `cancel_all`).
- Useful context helpers via prompts and resources.
- Built-in prompt templates: `trade_plan`, `risk_checklist`, `cancel_plan`, `onboarding_plan`.

## Setup

### 1. Environment Variables

Copy the example and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `AEVO_ENVIRONMENT` | No | `testnet` (default) or `mainnet` |
| `AEVO_API_KEY` | Yes* | API key from [AEVO settings](https://app.aevo.xyz/settings/api-keys) |
| `AEVO_API_SECRET` | Yes* | API secret from [AEVO settings](https://app.aevo.xyz/settings/api-keys) |
| `AEVO_SIGNING_KEY_PRIVATE_KEY` | Yes | Signing key for order submission |
| `AEVO_WALLET_ADDRESS` | No | Wallet address (only for `register_account` tool) |
| `AEVO_WALLET_PRIVATE_KEY` | No | Wallet private key (only for `register_account` tool) |
| `AEVO_AUTO_REGISTER` | No | Auto-register signing key + API key on startup (`true`/`false`) |
| `AEVO_MCP_TRANSPORT` | No | `stdio` (default) or `streamable-http` |
| `AEVO_MCP_HOST` | No | Host for HTTP transport (default `0.0.0.0`) |
| `AEVO_MCP_PORT` | No | Port for HTTP transport (default `8080`) |
| `AEVO_MCP_PATH` | No | Path for HTTP transport (default `/mcp`) |

\* If you don't have API keys yet, set `AEVO_WALLET_ADDRESS` + `AEVO_WALLET_PRIVATE_KEY` and use the `register_account` tool (or `AEVO_AUTO_REGISTER=true`) to generate them.

### 2. Local Install

```bash
pip install -e .
cp .env.example .env  # edit with your credentials
aevo-mcp --transport stdio
```

### 3. Docker

```bash
cp .env.example .env  # edit with your credentials
docker compose up --build
```

This exposes a streamable-http endpoint at `http://localhost:8080/mcp`.

### 4. Connect to Claude Code CLI

**Option A: stdio (local install)**

```bash
claude mcp add --transport stdio aevo-trading \
  --env AEVO_API_KEY=your_key \
  --env AEVO_API_SECRET=your_secret \
  --env AEVO_SIGNING_KEY_PRIVATE_KEY=your_signing_key \
  -- aevo-mcp --transport stdio
```

**Option B: HTTP (Docker)**

```bash
docker compose up -d
claude mcp add --transport http aevo-trading http://localhost:8080/mcp
```

> A `.mcp.json` project config is included in this repo. If you open this project in Claude Code with `aevo-mcp` installed locally, the server is auto-configured.

### 5. Connect to Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

**Option A: stdio (local install)**

```json
{
  "mcpServers": {
    "aevo-trading": {
      "command": "aevo-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "AEVO_API_KEY": "your_key",
        "AEVO_API_SECRET": "your_secret",
        "AEVO_SIGNING_KEY_PRIVATE_KEY": "your_signing_key"
      }
    }
  }
}
```

**Option B: HTTP (Docker)**

```json
{
  "mcpServers": {
    "aevo-trading": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

## Notes

- Register payload requires these exact AEVO keys: `account`, `signing_key`, `expiry`, `account_signature`, `signing_key_signature`.
- `create_order` payload uses required AEVO order fields:
  - `instrument`, `maker`, `is_buy`, `amount`, `limit_price`, `salt`, `signature`, `timestamp`
  - optional: `post_only`, `reduce_only`, `time_in_force`, `mmp`

## Prompts

- `trade_plan(symbol, side, amount, limit_price, time_in_force="GTC", post_only=False, reduce_only=False)`
  - Generates a deterministic pre-trade plan and execution order.
- `risk_checklist()`
  - Returns pre-trade safety checks.
- `cancel_plan(order_id="")`
  - Returns cancellation decision steps for a specific or unknown order.
- `onboarding_plan()`
  - Walks through first-run setup for new agent sessions.

## MCP Resources

- `aevo://status` -> output from `status` tool
- `aevo://markets/summary` -> snapshot of `markets()` payload
- `aevo://account/overview` -> snapshot of `account()` payload

## Tests

```bash
pytest -q tests/
```
