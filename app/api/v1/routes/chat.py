from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.exceptions import LLMError
from app.dependencies import get_chat_service
from app.schema.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    try:
        answer = await service.answer(payload.prompt)
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM upstream error: {exc}",
        ) from exc
    return ChatResponse(answer=answer)
