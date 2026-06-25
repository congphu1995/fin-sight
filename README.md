# FinSight

A headless **MCP server** for Vietnamese-equity research and live SSI market/account data.
It is consumed by an external agent ("Mira") over the Model Context Protocol — FinSight does
not chat; it collects, stores, and serves read-only tools.

Two tiers:

- **Tier 1 — background collection → DB.** A scheduler periodically crawls analyst reports
  (Vietstock), summarizes them with Gemini, and stores them in Postgres + MinIO, so the agent can
  pull pre-digested per-stock analyses cheaply.
- **Tier 2 — live SSI on demand.** Market data (SSI FastConnect **Data**) and your own account
  (SSI FastConnect **Trading**, **read-only** — positions/balances/orders, never order placement).

## Stack

- Python 3.12, [uv](https://docs.astral.sh/uv/)
- FastAPI · the official `mcp` SDK (FastMCP, streamable-HTTP)
- SQLAlchemy 2 (async) · asyncpg · Alembic · MinIO
- Google Gemini via `google-genai` (PDF extraction only)
- SSI via `ssi-fc-data` + `ssi-fctrading`
- pytest · ruff

## Quickstart

```bash
uv sync
cp .env.example .env          # fill GEMINI_API_KEY; SSI_* + MCP_AUTH_TOKEN optional
(cd ../infra && docker compose up -d)   # shared Postgres + MinIO (auto-provisions finsight DB + bucket)
uv run alembic upgrade head
uv run uvicorn app.main:app --reload    # API on :8000, MCP at /mcp

# one-off backfill (the scheduler also runs this on a timer)
uv run python -m app.reports
```

## Endpoints

| Method | Path             | Notes                                           |
|--------|------------------|-------------------------------------------------|
| GET    | `/api/v1/health` | `{"status":"ok"}`                               |
| —      | `/mcp`           | MCP streamable-HTTP (Mira connects here)        |

### MCP tools

- **Tier 1 (stored):** `get_stock_analysis`, `search_reports`, `get_report_metrics`,
  `list_facets`, `ask_report_pdf`
- **Tier 2 (live SSI, if configured):** `ssi_daily_ohlc`, `ssi_securities`,
  `ssi_index_components`, `ssi_daily_price`; `ssi_my_positions`, `ssi_my_cash_balance`,
  `ssi_my_orders`, `ssi_my_deriv_positions`

All tools are `readOnlyHint=True`. The SSI Trading client implements **read methods only** —
order placement is absent from the codebase, not merely gated.

### Connecting Mira

Add one entry to Mira's `MCP_SERVERS` (static bearer auth):

```json
{"name":"finsight","transport":"http","url":"https://<host>/mcp","auth":"none",
 "read_only_tools":["get_stock_analysis","search_reports","get_report_metrics","list_facets",
   "ask_report_pdf","ssi_daily_ohlc","ssi_securities","ssi_index_components","ssi_daily_price",
   "ssi_my_positions","ssi_my_cash_balance","ssi_my_orders","ssi_my_deriv_positions"]}
```

Set the same secret as `MCP_AUTH_TOKEN` here and as Mira's `MCP_FINSIGHT_TOKEN`
(or inline in the `headers`). Generate one with
`python -c "import secrets; print(secrets.token_urlsafe(32))"`.

## Configuration

All config is `.env` via `pydantic-settings` (see `.env.example`). Key groups:

| Var | Notes |
|-----|-------|
| `GEMINI_API_KEY` / `GEMINI_MODEL` | report extraction + `ask_report_pdf` |
| `DATABASE_URL`, `MINIO_*` | Tier-1 storage |
| `REFRESH_INTERVAL_HOURS` | background crawl cadence (0 disables; use a cron instead) |
| `MCP_AUTH_TOKEN`, `MCP_PATH` | MCP bearer + mount path |
| `SSI_DATA_*` | FastConnect Data creds (market data) |
| `SSI_TRADING_*` | FastConnect Trading creds + account; **read-only** |

### Where tokens live

- **Long-lived secrets** (SSI consumer id/secret, PIN, account, MCP token) → `.env`.
  The Trading **PEM private key** is a mounted file (`SSI_TRADING_PRIVATE_KEY_PATH`,
  default `secrets/ssi_private_key.pem`); `secrets/` is gitignored.
- **Short-lived SSI access tokens** (8h) → in-memory inside each client; the SDK refreshes them.
  Reads use the Trading **read token** (no PIN/2FA verify); the write token is never minted.
- **MCP bearer** → the shared static secret above.

## Development

```bash
uv run pytest tests/unit -q     # fast, no infra
uv run pytest                   # full suite (integration needs postgres+minio up)
uv run ruff check . && uv run ruff format --check .
uv run alembic revision --autogenerate -m "..."
```

See [CLAUDE.md](CLAUDE.md) for architecture and conventions.
