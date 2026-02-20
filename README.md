# AEVO MCP Server

A Model Context Protocol server for interacting with AEVO trading APIs.

## Features

- Register signing key and request API key/secret via EIP-712 payloads.
- Read account data: `account`, `portfolio`, `positions`, `markets`, `assets`, `orderbook`, `instrument`.
- Build and submit signed orders (`build_order`, `create_order`).
- Cancel and inspect open orders (`list_orders`, `get_order`, `cancel_order`, `cancel_orders`, `cancel_all`).
- Useful context helpers via prompts and resources.
- Built-in prompt templates: `trade_plan`, `risk_checklist`, `cancel_plan`, `onboarding_plan`.

## Environment

See `.env.example` and set:

- `AEVO_ACCOUNT_ADDRESS`
- `AEVO_ACCOUNT_PRIVATE_KEY`
- `AEVO_SIGNING_KEY`
- `AEVO_SIGNING_KEY_PRIVATE_KEY`
- optional `AEVO_API_KEY` and `AEVO_API_SECRET` for immediate access.

> No dry-run or policy-rules are built in. This keeps the server focused on AEVO contract primitives.

## Quick run (local)

```bash
python -m pip install -e .
cp .env.example .env   # optional
# edit .env
aevo-mcp --transport stdio
```

## Run with HTTP transport

```bash
aevo-mcp --transport streamable-http --host 127.0.0.1 --port 8080 --path /mcp
```

## Docker

```bash
docker compose up --build
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

## MCP resources

- `aevo://status` -> output from `status` tool
- `aevo://markets/summary` -> snapshot of `markets()` payload
- `aevo://account/overview` -> snapshot of `account()` payload

## Available tests

- `pytest -q tests`
