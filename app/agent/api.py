from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.agent.agents import AGENT_REGISTRY
from app.agent.agents.base import AgentSpec
from app.agent.dependencies import get_agent_spec, get_conversation_service
from app.agent.schemas import (
    AgentDTO,
    ConversationDTO,
    CreateConversationResponse,
    GetConversationResponse,
    ListAgentsResponse,
    MessageDTO,
    PostMessageRequest,
    PostMessageResponse,
)
from app.agent.service import ConversationNotFoundError, ConversationService
from app.core.exceptions import AgentLoopExceededError, LLMError

router = APIRouter(prefix="/agent", tags=["agent"])

ServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]
SpecDep = Annotated[AgentSpec, Depends(get_agent_spec)]


@router.get("/agents", response_model=ListAgentsResponse)
async def list_agents() -> ListAgentsResponse:
    """Discovery: which agents this server exposes."""
    return ListAgentsResponse(
        agents=[
            AgentDTO(key=s.key, description=s.description, tool_names=list(s.tool_names))
            for s in AGENT_REGISTRY.values()
        ]
    )


@router.post(
    "/{agent_key}/conversations",
    response_model=CreateConversationResponse,
    status_code=201,
)
async def create_conversation(
    spec: SpecDep, service: ServiceDep
) -> CreateConversationResponse:
    conv = await service.create_conversation(spec.key)
    return CreateConversationResponse(id=conv.id, agent_key=conv.agent_key)


@router.get(
    "/{agent_key}/conversations/{conversation_id}",
    response_model=GetConversationResponse,
)
async def get_conversation(
    spec: SpecDep,
    conversation_id: UUID,
    service: ServiceDep,
) -> GetConversationResponse:
    try:
        conv = await service.get_conversation(spec.key, conversation_id)
        messages = await service.list_messages(spec.key, conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="conversation not found") from exc
    return GetConversationResponse(
        conversation=ConversationDTO.model_validate(conv),
        messages=[MessageDTO.model_validate(m) for m in messages],
    )


@router.post(
    "/{agent_key}/conversations/{conversation_id}/messages",
    response_model=PostMessageResponse,
)
async def post_message(
    spec: SpecDep,
    conversation_id: UUID,
    payload: PostMessageRequest,
    service: ServiceDep,
) -> PostMessageResponse:
    try:
        new = await service.post_message(spec, conversation_id, payload.message)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="conversation not found") from exc
    except AgentLoopExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"agent loop exceeded budget: {exc}",
        ) from exc
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM upstream error: {exc}",
        ) from exc
    return PostMessageResponse(messages=[MessageDTO.model_validate(m) for m in new])
