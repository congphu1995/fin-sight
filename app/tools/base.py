"""Tool protocol, per-call context, and process-global registry.

A `Tool` knows its name, description, args schema, and how to run. The MCP
server wraps a selected subset of `TOOL_REGISTRY` as MCP tools; nothing imports
tool implementations directly.

To add a new tool: subclass Tool, decorate with @register, drop the file in
this package, and add the import to `app/tools/__init__.py`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm.gemini import GeminiClient
from app.core.ssi import SsiDataClient, SsiTradingClient
from app.core.storage.minio_client import MinioClient


@dataclass
class ToolContext:
    """Per-call handles passed to every tool invocation. Built per MCP call
    (or test) from the cross-feature singletons in `app/dependencies.py`.

    `ssi_data` / `ssi_trading` are None unless those integrations are
    configured; the SSI tools degrade to a "not configured" message then."""

    session: AsyncSession
    minio: MinioClient
    gemini: GeminiClient
    logger: structlog.stdlib.BoundLogger
    ssi_data: SsiDataClient | None = None
    ssi_trading: SsiTradingClient | None = None


class Tool(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    args_schema: ClassVar[type[BaseModel]]

    @abstractmethod
    async def run(self, args: BaseModel, ctx: ToolContext) -> dict:
        """Execute the tool. Bounded failures (no rows, 404, parse error) must
        be returned as `{"error": "..."}` so the model can recover. Only infra
        failures (DB down, MinIO down) raise."""


TOOL_REGISTRY: dict[str, Tool] = {}


def register(cls: type[Tool]) -> type[Tool]:
    if cls.name in TOOL_REGISTRY:
        raise RuntimeError(f"duplicate tool name {cls.name!r}")
    TOOL_REGISTRY[cls.name] = cls()
    return cls
