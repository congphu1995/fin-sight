# Cross-feature singletons only (engine, session factory, gemini, minio).
# Per-feature wiring lives in app/<feature>/dependencies.py.
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.database.session import make_engine, make_session_factory
from app.core.llm.gemini import GeminiClient
from app.core.storage.minio_client import MinioClient

SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    return make_engine(get_settings())


@lru_cache(maxsize=1)
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return make_session_factory(get_engine())


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@lru_cache(maxsize=1)
def get_gemini() -> GeminiClient:
    settings = get_settings()
    return GeminiClient(
        api_key=settings.gemini_api_key.get_secret_value(),
        model=settings.gemini_model,
    )


@lru_cache(maxsize=1)
def get_minio_client() -> MinioClient:
    settings = get_settings()
    return MinioClient(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key.get_secret_value(),
        secret_key=settings.minio_secret_key.get_secret_value(),
        bucket=settings.minio_bucket,
        secure=settings.minio_secure,
    )


def get_logger() -> structlog.stdlib.BoundLogger:
    return structlog.get_logger()
