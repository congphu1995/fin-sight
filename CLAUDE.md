# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands run through `uv` (Python 3.12). Dependencies are in `pyproject.toml`; `uv sync` installs them into `.venv`.

```bash
# Install / update deps (also creates .venv on first run)
uv sync

# First-time: copy env template, then fill in GEMINI_API_KEY
cp .env.example .env

# Postgres + MinIO + bucket bootstrap (matches DATABASE_URL / MINIO_* in .env)
docker compose up -d        # start
docker compose down         # stop (keeps data)
docker compose down -v      # stop and wipe data
# MinIO console: http://localhost:9001 (minioadmin/minioadmin)

# Run the API (reload mode for dev)
uv run uvicorn app.main:app --reload

# Reports pipeline (idempotent; safe to re-run)
uv run python -m app.reports                          # all enabled (source, type)
uv run python -m app.reports --type 58 --ticker HPG   # one type, one ticker
uv run python -m app.reports --only=extract           # single stage (after a prompt change)

# Lint
uv run ruff check .

# Tests (see "Tests" section below for layout + single-test commands)
uv run pytest
uv run pytest tests/unit -q
uv run pytest tests/integration -q

# Alembic — URL is read from .env via app.core.config, not alembic.ini
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

A `.env` is required (copy from `.env.example`). `Settings` (`app/core/config.py`) reads it via `pydantic-settings`. Without a real `GEMINI_API_KEY` the chat endpoint will 502; without Postgres the lifespan logs a warning but the app still starts and the chat endpoint still works (DB is currently scaffolded but unused).

## Architecture

The app is a thin layered service: **HTTP route → Service → external client (LLM / DB)**. Routes do validation + error mapping only; services own the business logic; clients (`GeminiClient`, SQLAlchemy session) are pure transport and raise domain exceptions, never log.

### Dependency injection — single source of truth

Cross-feature singletons live in `app/dependencies.py` — engine, session factory, Gemini, MinIO, settings — all `@lru_cache(maxsize=1)`. Per-request objects (`get_session`) are async generators that handle rollback + close. Feature-local wiring (e.g. building a `ReportSource` for a given source code) lives in `app/<feature>/dependencies.py` and depends on the cross-feature file. Tests override deps via `app.dependency_overrides` in `tests/integration/conftest.py` — see `FakeGeminiClient` / `FakeMinioClient` in `tests/base.py` for the canonical pattern.

The lifespan in `app/main.py` reuses the same `get_engine()` singleton from `dependencies.py` and calls `cache_clear()` after `engine.dispose()` on shutdown so a hot-reloaded process gets a fresh engine.

### Exceptions

Domain exceptions live in `app/core/exceptions.py`, **not** co-located with the code that raises them. `GeminiClient.generate` raises `LLMError`; the chat route catches it and maps to `HTTPException(502)`. New domain exceptions go in `core/exceptions.py` and are imported where needed.

### Feature layout — schemas vs. models

The codebase is feature-based: `app/chat/`, `app/health/`, `app/reports/`. Inside each feature:

- `schemas.py` — Pydantic models for API request/response. This is what FastAPI serializes.
- `models.py` (when the feature owns tables) — SQLAlchemy ORM mapped to `app/models/base.py:Base`. Alembic picks up everything bound to `Base.metadata` via `target_metadata = Base.metadata` in `alembic/env.py`.
- `api.py`, `service.py`/`services/` — route layer + business logic.

Cross-cutting infra stays under `app/core/` (LLM, DB, storage, logging, config, exceptions). API DTOs and ORM models are not interchangeable — don't import a feature's `models.py` into another feature's routes.

### Logging

`app/core/logging/setup.py` configures structlog with two renderers (dev=`ConsoleRenderer`, prod=`JSONRenderer`) and bridges stdlib logging (uvicorn, sqlalchemy) into the same pipeline. The processor chain includes `merge_contextvars`, so anything bound to `structlog.contextvars` automatically appears on every log line.

`app/core/logging/middleware.py` is registered in `main.py` as an HTTP middleware. It honors an incoming `X-Request-ID` header (or mints a UUID4), binds `request_id`/`method`/`path` to contextvars, and echoes the ID back in the response. This means every log line within a request is automatically correlated by `request_id` — you don't need to pass loggers around.

**When to log:** boundary events (service-level start/done, lifecycle, unexpected-but-recovered). **Don't log:** inside `core/llm/` or `core/database/` (raise instead — the caller decides), inside routes (uvicorn already logs the HTTP call), or in hot loops. Log shapes (lengths, IDs), never contents (no PII).

### Reports pipeline (`app/reports/`)

Three idempotent stages, each gated on `Report.status`:
`discovered → downloaded → extracted` (terminal: `duplicate`, `failed`).
Re-runs over already-processed rows do zero work — that's the recovery model.

Two registries, both **explicit**:
- `app/reports/crawlers/` — `ReportSource` ABC + `@register` decorator.
  New source = subclass + `@register` + INSERT into `sources`.
- `app/reports/extraction/registry.py` — explicit dict `EXTRACTION_REGISTRY`.
  Each `<key>/` folder pairs `schema.py` (Pydantic + `__extraction_key__` + `__version__`)
  with `prompt.md`. New schema = mkdir + 2 files + 1 import + 1 dict line + DB row.

Full design context: `docs/reports-pipeline.md` (gitignored, local only).

### Alembic

Async template. `alembic/env.py` calls `config.set_main_option("sqlalchemy.url", get_settings().database_url)`, so the `sqlalchemy.url` field in `alembic.ini` is intentionally blank. Don't set it there — change `DATABASE_URL` in `.env`.

### Tests

`pytest-asyncio` in `asyncio_mode = "auto"` (configured in `pyproject.toml`), so test functions can be `async def` without decorators.

**Layout — split by what the test exercises, not by what it covers:**

```
tests/
├── base.py                # shared utilities (e.g. FakeGeminiClient) — no fixtures
├── unit/                  # pure, fast, no I/O — service logic with mocked clients,
│                          # schema validation, pure functions in core/. No FastAPI app.
└── integration/           # exercise wiring: HTTP via ASGITransport, real DB session
    ├── conftest.py        # env-var setup BEFORE importing app.main; AsyncClient,
    │                      # app, fake_gemini fixtures; dependency_overrides cleanup
    └── test_*.py          # full request → response, with external clients faked
```

Rules:
- A test that imports `app.main` or constructs an `AsyncClient` is integration. It goes in `tests/integration/`.
- A test that instantiates a service or core class directly (no FastAPI, no real DB) is unit. It goes in `tests/unit/`.
- Shared test doubles (like `FakeGeminiClient`) live in `tests/base.py`. Fixtures live in the relevant `conftest.py` — `tests/integration/conftest.py` for HTTP-layer fixtures.
- Don't import from `tests/integration/` in unit tests, or vice versa.

Run a single test:
```bash
uv run pytest tests/integration/chat/test_chat.py::test_chat_returns_fake_answer -v
uv run pytest tests/unit -q                  # unit only
uv run pytest tests/integration -q           # integration only
```

## Gotchas

- **Gemini structured output rejects `additionalProperties`** in the JSON schema.
  Pydantic generates that for `dict[str, T]` fields. In any model passed as
  `response_schema` to `GeminiClient.generate_from_pdf`, use `list[NamedMetric]`
  (where `NamedMetric{name: str, value: float}`) instead of `dict[str, float]`.
  See `app/reports/extraction/company/schema.py` for the pattern.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/): `<type>: <imperative summary>` in the title, under ~70 chars.

Common types:

| Type     | Use for                                                                  |
|----------|--------------------------------------------------------------------------|
| `feat`   | A new user-facing capability (new endpoint, new field, new flag)         |
| `fix`    | A bug fix                                                                |
| `refactor` | Code restructure with no behavior change                                |
| `chore`  | Tooling, deps, build, env, infra (Dockerfile, ruff config, .gitignore)   |
| `docs`   | Documentation only                                                       |
| `test`   | Adding or restructuring tests, no production change                      |
| `perf`   | Performance improvement                                                  |

Guidelines:
- **Title is the why-shaped summary**, not a file list. `feat: add request-ID propagation` not `feat: add middleware.py`.
- **Imperative mood** ("add", "fix", "remove" — not "added"/"adds").
- **Body only when needed** — if the title is enough, skip the body. When you do add one, explain *why*, not *what* (the diff shows what).
- **One logical change per commit.** If you can describe two unrelated things in the message, split it.
- Don't include "AI generated" / co-author trailers unless explicitly asked.
