# FinSight

FastAPI service that answers user prompts via Google Gemini. Scaffolded with PostgreSQL (async), Alembic, structlog, and Pydantic — DB is wired but unused by the first feature.

## Stack

- Python 3.12, [uv](https://docs.astral.sh/uv/) for env + deps
- FastAPI · Pydantic · structlog
- SQLAlchemy 2 (async) · asyncpg · Alembic
- Google Gemini via `google-genai`
- pytest · ruff

## Quickstart

```bash
uv sync                       # install deps into .venv
cp .env.example .env          # then fill in GEMINI_API_KEY
uv run uvicorn app.main:app --reload
```

Server runs at `http://127.0.0.1:8000`. OpenAPI docs at `/docs`.

Postgres is optional for local dev — the app starts without it (lifespan logs a warning) and the chat endpoint still works.

## Endpoints

| Method | Path                | Body                  | Returns          |
|--------|---------------------|-----------------------|------------------|
| GET    | `/api/v1/health`    | —                     | `{"status":"ok"}`|
| POST   | `/api/v1/chat`      | `{"prompt": "..."}`   | `{"answer":"..."}`|

```bash
curl http://127.0.0.1:8000/api/v1/health
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Say hi in one word."}'
```

Every response carries an `X-Request-ID` header (echoed if you supply one, otherwise generated) and that ID appears on every log line for the request.

## Configuration

All config is read from `.env` via `pydantic-settings`. See `.env.example`:

| Var              | Default                                                          | Notes                                       |
|------------------|------------------------------------------------------------------|---------------------------------------------|
| `ENV`            | `dev`                                                            | `dev` → console logs, `prod` → JSON logs    |
| `LOG_LEVEL`      | `INFO`                                                           |                                             |
| `DATABASE_URL`   | `postgresql+asyncpg://finsight:finsight@localhost:5432/finsight` | Used by SQLAlchemy and Alembic              |
| `GEMINI_API_KEY` | —                                                                | Required for `/chat`                        |
| `GEMINI_MODEL`   | `gemini-flash-lite-latest`                                       |                                             |

## Project layout

```
app/
├── main.py                 # FastAPI app + lifespan
├── dependencies.py         # FastAPI DI: singletons + per-request session
├── api/v1/                 # routers (health, chat) + aggregator
├── schema/                 # Pydantic request/response models
├── models/                 # SQLAlchemy ORM (Base only for now)
├── services/               # business logic, injected into routes
└── core/
    ├── config.py           # Settings (pydantic-settings)
    ├── exceptions.py       # domain exceptions (LLMError, ...)
    ├── logging/            # structlog setup + request-ID middleware
    ├── database/session.py # async engine + session factory
    └── llm/gemini.py       # Gemini client wrapper
alembic/                    # async migrations; URL read from Settings
tests/                      # pytest-asyncio (auto mode) + httpx AsyncClient
```

## Development

```bash
uv run pytest                                              # all tests
uv run pytest tests/test_chat.py::test_chat_returns_fake_answer -v
uv run ruff check .                                        # lint

# Alembic — DATABASE_URL comes from .env, not alembic.ini
uv run alembic revision --autogenerate -m "add chat_message table"
uv run alembic upgrade head
```

Tests use a `FakeGeminiClient` (`tests/base.py`) injected via `app.dependency_overrides` — no real API calls or DB needed.
