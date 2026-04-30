"""ConversationService: persistence + agent-loop orchestration.

The service is **agent-agnostic** — it takes an `AgentSpec` per call,
constructs a fresh `AgentLoop` configured for that spec, then runs and
persists the resulting events.

The loop yields events; we persist each one in its own commit so partial
progress (e.g. tool calls already made) survives a mid-turn failure. The
caller route maps domain exceptions to HTTP.
"""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agents.base import AgentSpec
from app.agent.models import Conversation, Message
from app.agent.runtime.loop import AgentLoop, HistoryMessage, LoopEvent
from app.agent.tools.base import Tool, ToolContext
from app.core.llm.gemini import GeminiClient


class ConversationNotFoundError(Exception):
    """Raised when a requested conversation does not exist for the given agent."""


class ConversationService:
    def __init__(
        self,
        session: AsyncSession,
        gemini: GeminiClient,
        ctx: ToolContext,
        tool_registry: dict[str, Tool],
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        self._session = session
        self._gemini = gemini
        self._ctx = ctx
        self._tools = tool_registry
        self._logger = logger

    async def create_conversation(self, agent_key: str) -> Conversation:
        conv = Conversation(agent_key=agent_key)
        self._session.add(conv)
        await self._session.commit()
        await self._session.refresh(conv)
        return conv

    async def get_conversation(self, agent_key: str, conv_id: UUID) -> Conversation:
        conv = await self._session.get(Conversation, conv_id)
        if conv is None or conv.agent_key != agent_key:
            raise ConversationNotFoundError(str(conv_id))
        return conv

    async def list_messages(self, agent_key: str, conv_id: UUID) -> list[Message]:
        # Ownership check — raises if conv missing or wrong agent.
        await self.get_conversation(agent_key, conv_id)
        stmt = (
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def post_message(
        self, spec: AgentSpec, conv_id: UUID, user_text: str
    ) -> list[Message]:
        conv = await self.get_conversation(spec.key, conv_id)
        prior_orm = await self._fetch_history(conv_id)
        prior = [_to_history(m) for m in prior_orm]

        loop = self._build_loop(spec)

        self._logger.info(
            "agent.turn.start",
            agent_key=spec.key,
            conversation_id=str(conv_id),
            prior_messages=len(prior),
            user_text_length=len(user_text),
        )

        new_messages: list[Message] = []
        try:
            async for event in loop.run_turn(
                prior=prior,
                user_text=user_text,
                system_instruction=spec.system_prompt,
                enable_google_search=spec.enable_google_search,
            ):
                msg = await self._persist(conv.id, event)
                new_messages.append(msg)
        except Exception as exc:
            self._logger.warning(
                "agent.turn.failed",
                agent_key=spec.key,
                conversation_id=str(conv_id),
                partial_messages=len(new_messages),
                error_type=type(exc).__name__,
            )
            raise

        # Bump conversation.updated_at so listings can sort by recency.
        await self._session.refresh(conv)
        await self._session.commit()

        self._logger.info(
            "agent.turn.done",
            agent_key=spec.key,
            conversation_id=str(conv_id),
            new_messages=len(new_messages),
        )
        return new_messages

    def _build_loop(self, spec: AgentSpec) -> AgentLoop:
        try:
            tools = {name: self._tools[name] for name in spec.tool_names}
        except KeyError as exc:
            raise RuntimeError(
                f"agent {spec.key!r} references unregistered tool {exc.args[0]!r}"
            ) from exc
        return AgentLoop(
            gemini=self._gemini,
            tools=tools,
            ctx=self._ctx,
            max_steps=spec.max_steps,
            per_tool_timeout_s=spec.per_tool_timeout_s,
            per_turn_timeout_s=spec.per_turn_timeout_s,
        )

    async def _fetch_history(self, conv_id: UUID) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def _persist(self, conv_id: UUID, event: LoopEvent) -> Message:
        kwargs: dict = {"conversation_id": conv_id, "step": event.step}
        if event.kind == "user":
            kwargs.update(role="user", content=event.text)
        elif event.kind == "assistant":
            kwargs.update(role="assistant", content=event.text)
        elif event.kind == "assistant_tool_call":
            kwargs.update(
                role="assistant",
                tool_call_id=event.tool_call_id,
                tool_name=event.tool_name,
                tool_args=event.tool_args,
            )
        elif event.kind == "tool_result":
            kwargs.update(
                role="tool",
                tool_call_id=event.tool_call_id,
                tool_name=event.tool_name,
                tool_result=event.tool_result,
            )
        else:  # pragma: no cover — unknown kind
            raise ValueError(f"unknown loop event kind: {event.kind}")

        msg = Message(**kwargs)
        self._session.add(msg)
        await self._session.commit()
        await self._session.refresh(msg)
        return msg


def _to_history(m: Message) -> HistoryMessage:
    return HistoryMessage(
        role=m.role,
        content=m.content,
        tool_call_id=m.tool_call_id,
        tool_name=m.tool_name,
        tool_args=m.tool_args,
        tool_result=m.tool_result,
    )
