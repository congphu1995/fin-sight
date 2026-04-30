"""Feature-local DI for the agent layer.

Cross-feature singletons (engine, gemini, minio) come from `app/dependencies.py`.
This module wires up the per-request `ToolContext`, the `ConversationService`,
and the path-param-driven `AgentSpec` lookup.
"""

from typing import Annotated

import structlog
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agents import AGENT_REGISTRY
from app.agent.agents.base import AgentSpec
from app.agent.service import ConversationService
from app.agent.tools import TOOL_REGISTRY
from app.agent.tools.base import ToolContext
from app.core.llm.gemini import GeminiClient
from app.core.storage.minio_client import MinioClient
from app.dependencies import (
    get_gemini,
    get_logger,
    get_minio_client,
    get_session,
)


def get_agent_spec(agent_key: str) -> AgentSpec:
    """Resolve `{agent_key}` from the URL path against the registry.

    Returns 404 if unknown — the route never sees an invalid spec.
    """
    spec = AGENT_REGISTRY.get(agent_key)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"unknown agent {agent_key!r}",
        )
    return spec


def get_tool_context(
    session: Annotated[AsyncSession, Depends(get_session)],
    minio: Annotated[MinioClient, Depends(get_minio_client)],
    gemini: Annotated[GeminiClient, Depends(get_gemini)],
    logger: Annotated[structlog.stdlib.BoundLogger, Depends(get_logger)],
) -> ToolContext:
    return ToolContext(session=session, minio=minio, gemini=gemini, logger=logger)


def get_conversation_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    gemini: Annotated[GeminiClient, Depends(get_gemini)],
    ctx: Annotated[ToolContext, Depends(get_tool_context)],
    logger: Annotated[structlog.stdlib.BoundLogger, Depends(get_logger)],
) -> ConversationService:
    return ConversationService(
        session=session,
        gemini=gemini,
        ctx=ctx,
        tool_registry=TOOL_REGISTRY,
        logger=logger,
    )
