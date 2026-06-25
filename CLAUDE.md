# CLAUDE.md

Guidance for working in this repo.

## What this is

FinSight is a **headless MCP server** consumed by an external agent ("Mira") over the Model
Context Protocol. It does NOT chat — it collects, stores, and serves **read-only** tools. Two tiers:

- **Tier 1 — background collection → DB.** A scheduler runs the reports pipeline (crawl Vietstock →
  download PDFs to MinIO → Gemini structured extraction → Postgres) so the agent can pull
  pre-digested per-stock analyses cheaply.
- **Tier 2 — live SSI on demand.** SSI FastConnect **Data** (market data) and FastConnect
  **Trading** (your account, **read-only**).

The agent orchestrates across both tiers; FinSight just exposes tools.

## Commands

All commands run through `uv` (Python 3.12).

```bash
uv sync
cp .env.example .env        # fill GEMINI_API_KEY; SSI_* + MCP_AUTH_TOKEN optional

(cd ../infra && docker compose up -d)   # shared Postgres + MinIO from ../infra (provisions finsight DB + bucket)
uv run alembic upgrade head

uv run uvicorn app.main:app --reload   # API on :8000, MCP at /mcp

# Reports pipeline (idempotent; the scheduler runs this on a timer, REFRESH_INTERVAL_HOURS)
uv run python -m app.reports
uv run python -m app.reports --type company --ticker HPG
uv run python -m app.reports --only=extract

uv run ruff check . && uv run ruff format --check .
uv run pytest tests/unit -q     # fast tier, no infra
uv run pytest                   # full (integration needs postgres+minio up)
```

## Architecture

Layered: **HTTP/MCP → tools/services → core clients (LLM / DB / storage / SSI)**.
Routes do validation + error mapping; tools/services own logic; core clients are pure transport.

```
app/
  main.py            # FastAPI app + lifespan (DB check, scheduler, MCP session manager); mounts /mcp
  dependencies.py    # @lru_cache singletons: engine, session factory, gemini, minio, ssi_data, ssi_trading
  scheduler.py       # ReportsScheduler — in-process tick that runs the pipeline
  api/v1/            # health router + aggregator (no chat routes — Mira is the agent)
  mcp/               # the MCP server
    server.py        #   build_mcp_server(settings) -> FastMCP; @mcp.tool wrappers over the registry
    render.py        #   dict -> concise text (empty-final-safe; ids inline, prose last line)
    auth.py          #   BearerAuthMiddleware (static token on the /mcp sub-app)
  tools/             # the read-only tool catalog (Tool ABC + @register + TOOL_REGISTRY)
    base.py          #   Tool + ToolContext(session, minio, gemini, logger, ssi_data?, ssi_trading?)
    get_stock_analysis.py  search_reports.py  get_report_metrics.py  list_facets.py  ask_report_pdf.py
    ssi_market.py    #   ssi_daily_ohlc/securities/index_components/daily_price (FC Data)
    ssi_account.py   #   ssi_my_positions/cash_balance/orders/deriv_positions (FC Trading reads)
  reports/           # Tier-1 pipeline: crawlers/, extraction/, services/, jobs.py, __main__.py, models.py
  core/
    config.py        #   Settings (pydantic-settings)
    ssi/             #   data_client.py + trading_client.py (async facades over the SSI SDKs)
    llm/gemini.py    #   GeminiClient: generate_from_pdf (extraction) + ask_about_pdf
    storage/minio_client.py  database/session.py  logging/  exceptions.py
alembic/             # async migrations (URL from Settings)
```

### Dependency injection

Cross-feature singletons live in `app/dependencies.py`, all `@lru_cache(maxsize=1)`:
engine, session factory, gemini, minio, and `get_ssi_data_client` / `get_ssi_trading_client`
(return `None` when their creds aren't configured). The lifespan reuses the same engine singleton
and `cache_clear()`s it on shutdown.

### MCP server (`app/mcp/`)

`build_mcp_server(settings)` returns a `FastMCP` whose tools wrap `TOOL_REGISTRY`. Each wrapper takes
the underlying tool's Pydantic `args_schema` as its single parameter (one source of truth for the
input schema) and returns rendered **text**. Every tool is `annotations=ToolAnnotations(readOnlyHint=
True)` so Mira auto-runs them with no approval card. SSI tools register only when configured.

- **Mounting is load-bearing.** `main.py` builds the server at import, mounts
  `streamable_http_app()` at `MCP_PATH` (built with `streamable_http_path="/"` so the endpoint is
  exactly `/mcp`), and **runs `mcp.session_manager.run()` in the lifespan** — mounting alone does NOT
  start the transport.
- **Auth:** `BearerAuthMiddleware` on the sub-app checks `Authorization: Bearer <MCP_AUTH_TOKEN>`
  (constant-time). Empty token disables it (private-tailnet only); it guards `/mcp`, not `/healthz`.
- **Output rule (`render.py`):** Mira's Gemini emits an empty final answer when a tool result *ends*
  on a line of opaque tokens (ids/hashes). So renderers put ids **inline mid-line** and always end on
  a prose/summary line. A test asserts this. If you change a renderer, keep that invariant.

### SSI (`app/core/ssi/`, Tier 2)

Two async facades over the official **sync** SDKs (wrapped in `asyncio.to_thread`, mirroring
`MinioClient`), each with lazy construction (the SDK constructors do network), a serialization lock,
an in-memory 8h token cache (the SDK refreshes), and a short-TTL response cache.

- `data_client.py` (`ssi-fc-data`): market data. Auth = consumer id/secret → token.
- `trading_client.py` (`ssi-fctrading`): **READ-ONLY** account access. **The hard guarantee:** the
  facade exposes only read verbs (`stock_position`, `cash_balance`, `order_book`, …) and NEVER calls
  `verifyCode`/`new_order`/`modify_order`/`cancle_order`/`create_*`. In the SDK, reads use a *read*
  token (consumer id/secret, no 2FA code); writes need a *write* token minted by `verifyCode(pin)` +
  an RSA signature — which this facade never does, so no order can be placed. A test
  (`test_trading_client_exposes_only_read_methods`) pins the public surface. Never add a write verb here.
- **PIN deprecation risk:** SSI is phasing out PIN 2FA toward OTP (which can't run unattended). Reads
  don't currently need the PIN; if SSI changes read-token issuance this needs revisiting. Market data
  is unaffected.

### Where tokens live

- Long-lived secrets (SSI consumer id/secret, PIN, account, `MCP_AUTH_TOKEN`) → `.env`. The Trading
  **PEM** is a mounted file (`SSI_TRADING_PRIVATE_KEY_PATH`, default `secrets/ssi_private_key.pem`);
  `secrets/` is gitignored.
- Short-lived SSI access tokens (8h) → in-memory inside each client; never persisted.
- MCP bearer → the shared static secret, mirrored as Mira's `MCP_FINSIGHT_TOKEN`.

### Scheduler (`app/scheduler.py`, Tier 1)

`ReportsScheduler` is an in-process asyncio tick started in the lifespan; every
`REFRESH_INTERVAL_HOURS` it runs `run_pipeline` (the same path as `python -m app.reports`), serial,
timeout-bounded, idempotent, never crashing the loop. `REFRESH_INTERVAL_HOURS <= 0` disables it
(use an external cron instead). Single-instance assumption (single-owner); split into a worker
process if you ever run multiple replicas.

### Reports pipeline (`app/reports/`)

Three idempotent stages gated on `Report.status`: `discovered → downloaded → extracted` (terminal:
`duplicate`, `failed`). Re-runs are no-ops on processed rows. Two explicit registries:

- `crawlers/` — `ReportSource` ABC + `@register`. Source quirks (e.g. Vietstock's `reportTypeID='58'`)
  live on the crawler class, never as columns. New source = subclass + `@register` + INSERT into `sources`.
- `extraction/registry.py` — `EXTRACTION_REGISTRY` keyed by the universal type slug (= `report_types.code`).
  Each `<key>/` folder pairs `schema.py` (Pydantic + `__extraction_key__` + `__version__`) with `prompt.md`.

Promoting a payload key to a typed column in `services/extractor.py`: update BOTH `_extract_facets`
and `_FACET_STRIP_KEYS` (the parametrized `test_extras_excludes_promoted_keys` enforces it).

### Tools (`app/tools/`)

`Tool` ABC: `name` + `description` + Pydantic `args_schema` + `async run(args, ctx) -> dict`,
registered via `@register` into `TOOL_REGISTRY`. Bounded failures return `{"error": "..."}`; only
infra failures raise. `get_stock_analysis` aggregates the latest `report_extractions` per ticker.
SSI tools degrade to a "not configured" dict when their client is `None`.

### Alembic

Async template; `alembic/env.py` sets `sqlalchemy.url` from Settings (blank in `alembic.ini`). Only
`app.reports.models` is imported for `target_metadata`. New revision:
`uv run alembic revision --autogenerate -m "..."`.

## Tests

`pytest-asyncio` in `asyncio_mode = "auto"` (async tests need no decorator). Split by what they
exercise:

- `tests/unit/` — pure, no I/O. `reports/` (pipeline logic), `mcp/` (in-memory MCP client via
  `mcp.shared.memory.create_connected_server_and_client_session` — tool listing + readOnlyHint +
  render invariants + bearer auth), `ssi/` (token cache + the read-only guarantee), `tools/` (SSI
  tool shaping + degrade).
- `tests/integration/` — full HTTP stack via `ASGITransport`; needs Postgres + MinIO up.
- Shared doubles in `tests/base.py` (`FakeGeminiClient`, `FakeMinioClient`, `FakeReportSource`).

DB-backed tools (`get_stock_analysis`, `search_reports`, …) need Postgres (the models use PG
ARRAY/JSONB), so they're covered in the integration tier, not unit. Live SSI calls need real creds —
not in any tier; verify with a small smoke script.

## Gotchas

- **Gemini structured output rejects `additionalProperties`** (Pydantic emits it for `dict[...]`
  fields). In any `response_schema`, use `list[NamedMetric]` instead of `dict[str, float]`. See
  `app/reports/extraction/company/schema.py`.
- **Empty-final rule** (above): tool output text must not end on an opaque-token line.
- **`REFRESH_ON_STARTUP=true`** runs a full crawl at boot — handy for a fresh DB, slow otherwise.
- **Mount path:** the MCP endpoint is `/mcp` only because the sub-app uses `streamable_http_path="/"`
  and is mounted at `/mcp`. Changing `MCP_PATH` changes the mount; keep them consistent.

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/): `<type>: <imperative summary>`, ~70 chars.
Common types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `perf`. Title is the why, imperative
mood, default to title-only. Don't include AI/co-author trailers.
