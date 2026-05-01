from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging.middleware import request_context_middleware
from app.core.logging.setup import configure_logging
from app.dependencies import get_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(env=settings.env, level=settings.log_level)
    logger = structlog.get_logger()

    engine = get_engine()
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("startup.db.ok")
    except Exception as exc:
        logger.warning("startup.db.unavailable", error=str(exc))

    logger.info("startup.complete", env=settings.env)
    try:
        yield
    finally:
        await engine.dispose()
        get_engine.cache_clear()
        logger.info("shutdown.complete")


app = FastAPI(title="FinSight", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(request_context_middleware)
app.include_router(api_router)
