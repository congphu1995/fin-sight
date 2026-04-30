from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateConversationResponse(BaseModel):
    id: UUID
    agent_key: str


class PostMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)


class MessageDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None
    step: int
    created_at: datetime


class PostMessageResponse(BaseModel):
    """All messages persisted during this turn (the user msg + every
    assistant/tool row produced by the agent loop)."""

    messages: list[MessageDTO]


class ConversationDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_key: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class GetConversationResponse(BaseModel):
    conversation: ConversationDTO
    messages: list[MessageDTO]


class AgentDTO(BaseModel):
    """Discovery DTO for `GET /api/v1/agent/agents`."""

    key: str
    description: str
    tool_names: list[str]


class ListAgentsResponse(BaseModel):
    agents: list[AgentDTO]
