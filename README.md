# AEVO MCP Server

MCP server for trading on [AEVO](https://app.aevo.xyz) — works with Claude Code, Claude Desktop, or any MCP client.

## Quick Start (Docker + Claude Code)

**1. Clone and configure**

```bash
git clone https://github.com/aevo-xyz/mcp-aevo-server.git
cd mcp-aevo-server
cp .env.example .env
```

Edit `.env` with your AEVO credentials (get them from [app.aevo.xyz/settings](https://app.aevo.xyz/settings/api-keys)):

```
AEVO_API_KEY=your_key
AEVO_API_SECRET=your_secret
AEVO_SIGNING_KEY_PRIVATE_KEY=your_signing_key
```

**2. Start the server**

```bash
docker compose up --build -d
```

**3. Connect Claude Code**

```bash
claude mcp add --transport http aevo-trading http://localhost:8080/mcp
```

**4. Test it**

Open a new Claude Code session and type:

```
call the ping tool
```

You should see `{"ok": true, "result": {"status": "ok"}}`. Try `check my account balance` to verify your credentials work.

## Alternative Setup

### Local (no Docker)

```bash
pip install -e .
cp .env.example .env   # edit with your credentials
aevo-mcp --transport stdio
```

Then connect Claude Code via stdio:

```bash
claude mcp add --transport stdio aevo-trading -- aevo-mcp --transport stdio
```

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

**With Docker (recommended):**

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

**With local install:**

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

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AEVO_API_KEY` | Yes* | API key |
| `AEVO_API_SECRET` | Yes* | API secret |
| `AEVO_SIGNING_KEY_PRIVATE_KEY` | Yes | Signing key for order submission |
| `AEVO_ENVIRONMENT` | No | `testnet` or `mainnet` (default) |
| `AEVO_WALLET_ADDRESS` | No | Wallet address (for `register_account` tool) |
| `AEVO_WALLET_PRIVATE_KEY` | No | Wallet private key (for `register_account` tool) |
| `AEVO_AUTO_REGISTER` | No | Auto-register on startup (`true`/`false`) |

\* Don't have API keys? Set `AEVO_WALLET_ADDRESS` + `AEVO_WALLET_PRIVATE_KEY` and use the `register_account` tool to generate them. Advise to have a account and use aevo wallet to generate keys.

## What's Included

**Tools:** `markets`, `account`, `portfolio`, `positions`, `orderbook`, `build_order`, `create_order`, `cancel_order`, `cancel_all`, `register_account`, and more.

**Prompts:** `trade_plan`, `risk_checklist`, `cancel_plan`, `onboarding_plan`

**Resources:** `aevo://status`, `aevo://markets/summary`, `aevo://account/overview`

## Tests

```bash
pip install -e ".[test]"
pytest -q tests/
```
