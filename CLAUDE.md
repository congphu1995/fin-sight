# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands run through `uv` (Python 3.12). Dependencies are in `pyproject.toml`; `uv sync` installs them into `.venv`.

```bash
# Install / update deps (also creates .venv on first run)
uv sync

# First-time: copy env template, then fill in GEMINI_API_KEY
cp .env.example .env

# Postgres (matches DATABASE_URL in .env)
docker compose up -d        # start
docker compose down         # stop (keeps data)
docker compose down -v      # stop and wipe data

# Run the API (reload mode for dev)
uv run uvicorn app.main:app --reload

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

All FastAPI dependencies live in `app/dependencies.py` (a flat file, not a package — intentional). Long-lived objects (engine, session factory, Gemini client, settings) are `@lru_cache(maxsize=1)` singletons; per-request objects (`get_session`) are async generators that handle rollback + close. Tests override these via `app.dependency_overrides` in `tests/conftest.py` — see `FakeGeminiClient` in `tests/base.py` for the canonical pattern.

The lifespan in `app/main.py` reuses the same `get_engine()` singleton from `dependencies.py` and calls `cache_clear()` after `engine.dispose()` on shutdown so a hot-reloaded process gets a fresh engine.

### Exceptions

Domain exceptions live in `app/core/exceptions.py`, **not** co-located with the code that raises them. `GeminiClient.generate` raises `LLMError`; the chat route catches it and maps to `HTTPException(502)`. New domain exceptions go in `core/exceptions.py` and are imported where needed.

### Schema vs. models

- `app/schema/` — Pydantic models for API request/response. This is what FastAPI serializes.
- `app/models/` — SQLAlchemy ORM (`DeclarativeBase`). Currently only `Base`; new tables go here and Alembic autogenerate picks them up via `target_metadata = Base.metadata` in `alembic/env.py`.

These are not interchangeable. Don't import `app/models/*` into routes; routes should consume services, which can consume both.

### Logging

`app/core/logging/setup.py` configures structlog with two renderers (dev=`ConsoleRenderer`, prod=`JSONRenderer`) and bridges stdlib logging (uvicorn, sqlalchemy) into the same pipeline. The processor chain includes `merge_contextvars`, so anything bound to `structlog.contextvars` automatically appears on every log line.

`app/core/logging/middleware.py` is registered in `main.py` as an HTTP middleware. It honors an incoming `X-Request-ID` header (or mints a UUID4), binds `request_id`/`method`/`path` to contextvars, and echoes the ID back in the response. This means every log line within a request is automatically correlated by `request_id` — you don't need to pass loggers around.

**When to log:** boundary events (service-level start/done, lifecycle, unexpected-but-recovered). **Don't log:** inside `core/llm/` or `core/database/` (raise instead — the caller decides), inside routes (uvicorn already logs the HTTP call), or in hot loops. Log shapes (lengths, IDs), never contents (no PII).

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
uv run pytest tests/integration/test_chat.py::test_chat_returns_fake_answer -v
uv run pytest tests/unit -q                  # unit only
uv run pytest tests/integration -q           # integration only
```

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
