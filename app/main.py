from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging.middleware import request_context_middleware
from app.core.logging.setup import configure_logging
from app.dependencies import get_engine
from app.mcp import build_mcp_server
from app.mcp.auth import BearerAuthMiddleware
from app.scheduler import ReportsScheduler

# Built at import: the MCP sub-app (creates the session manager run in the lifespan)
# and an optional static-bearer guard on its routes.
_settings = get_settings()
_mcp_server = build_mcp_server(_settings)
_mcp_app = _mcp_server.streamable_http_app()
_mcp_token = _settings.mcp_auth_token.get_secret_value()
if _mcp_token:
    _mcp_app.add_middleware(BearerAuthMiddleware, token=_mcp_token)


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

    scheduler = ReportsScheduler(settings, logger)
    scheduler.start()

    logger.info("startup.complete", env=settings.env, mcp_path=settings.mcp_path)
    try:
        # Mounting alone does NOT start the MCP transport — its session manager
        # must run inside the parent app's lifespan.
        async with _mcp_server.session_manager.run():
            yield
    finally:
        await scheduler.stop()
        await engine.dispose()
        get_engine.cache_clear()
        logger.info("shutdown.complete")


app = FastAPI(title="FinSight", lifespan=lifespan)
app.middleware("http")(request_context_middleware)
app.include_router(api_router)
app.mount(_settings.mcp_path, _mcp_app)
