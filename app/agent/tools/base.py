"""Tool protocol, per-request context, and process-global registry.

A `Tool` knows its name, description, args schema, and how to run. Agents
allowlist a subset of `TOOL_REGISTRY` via their `AgentSpec.tool_names`; the
loop never imports tool implementations directly.

To add a new tool: subclass Tool, decorate with @register, drop the file in
this package, and add the import to `app/agent/tools/__init__.py`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm.gemini import GeminiClient
from app.core.storage.minio_client import MinioClient


@dataclass
class ToolContext:
    """Per-request handles passed to every tool invocation. Built once per
    user turn from the cross-feature singletons in `app/dependencies.py`."""

    session: AsyncSession
    minio: MinioClient
    gemini: GeminiClient
    logger: structlog.stdlib.BoundLogger


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
