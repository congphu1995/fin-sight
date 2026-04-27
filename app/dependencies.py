from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

import structlog
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.database.session import make_engine, make_session_factory
from app.core.llm.gemini import GeminiClient
from app.services.chat_service import ChatService

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


def get_logger() -> structlog.stdlib.BoundLogger:
    return structlog.get_logger()


def get_chat_service(
    gemini: Annotated[GeminiClient, Depends(get_gemini)],
    logger: Annotated[structlog.stdlib.BoundLogger, Depends(get_logger)],
) -> ChatService:
    return ChatService(gemini=gemini, logger=logger)
