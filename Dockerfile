# syntax=docker/dockerfile:1

# The uv image ships Python 3.12. No frontend stage — fin-sight is headless (MCP + API only).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app

# Deps first so this layer caches until pyproject/lock change. README.md is needed because
# pyproject's `readme` is read when resolving project metadata.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

# App source + Alembic assets (migrations run on startup).
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# `app` is imported from the workdir (the project isn't installed as a wheel).
ENV PYTHONPATH=/app
EXPOSE 8000
# Apply migrations (idempotent) then serve; bind 0.0.0.0 for the in-network port.
CMD ["/bin/sh", "-c", ".venv/bin/alembic upgrade head && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000"]
