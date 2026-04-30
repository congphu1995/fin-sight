"""Agent tool-use loop.

Pure orchestration: LLM call → tool dispatch → repeat. Yields `LoopEvent`s as
they happen so the caller (ConversationService) can persist each one.

No DB, no FastAPI — only `GeminiClient`, the tool registry, and a `ToolContext`.
The loop is agent-agnostic: tools, prompt, and limits are passed in by
whichever `AgentSpec` is driving the turn.
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from google.genai import types as genai_types

from app.agent.tools.base import Tool, ToolContext
from app.core.exceptions import AgentLoopExceededError
from app.core.llm.gemini import FunctionDecl, GeminiClient

DEFAULT_MAX_STEPS = 10
DEFAULT_PER_TOOL_TIMEOUT_S = 45.0  # `ask_report_pdf` calls Gemini on a full PDF
DEFAULT_PER_TURN_TIMEOUT_S = 180.0


@dataclass
class HistoryMessage:
    """Minimal shape the loop needs from a persisted message."""

    role: str  # 'user' | 'assistant' | 'tool'
    content: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None


@dataclass
class LoopEvent:
    """An event the loop emits. Step 0 is the new user turn; steps ≥1 are
    rounds of LLM-call → tool-dispatch."""

    kind: str  # 'user' | 'assistant_tool_call' | 'tool_result' | 'assistant'
    step: int = 0
    text: str | None = None
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: dict[str, Any] | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)


class AgentLoop:
    def __init__(
        self,
        gemini: GeminiClient,
        tools: dict[str, Tool],
        ctx: ToolContext,
        *,
        max_steps: int = DEFAULT_MAX_STEPS,
        per_tool_timeout_s: float = DEFAULT_PER_TOOL_TIMEOUT_S,
        per_turn_timeout_s: float = DEFAULT_PER_TURN_TIMEOUT_S,
    ) -> None:
        self._gemini = gemini
        self._tools = tools
        self._ctx = ctx
        self._max_steps = max_steps
        self._per_tool_timeout_s = per_tool_timeout_s
        self._per_turn_timeout_s = per_turn_timeout_s

    async def run_turn(
        self,
        prior: list[HistoryMessage],
        user_text: str,
        *,
        system_instruction: str | None = None,
        enable_google_search: bool = False,
    ) -> AsyncIterator[LoopEvent]:
        async def _runner() -> AsyncIterator[LoopEvent]:
            yield LoopEvent(kind="user", step=0, text=user_text)

            # Cross-turn history: only user/assistant TEXT survives. Prior
            # function_call parts can't be replayed across turns because their
            # required `thought_signature` field is not persisted; the prior
            # assistant text already summarises whatever the model found.
            contents: list[genai_types.Content] = _to_gemini_contents(prior)
            contents.append(
                genai_types.Content(role="user", parts=[genai_types.Part(text=user_text)])
            )
            tool_decls = [_tool_to_decl(t) for t in self._tools.values()]

            for step in range(1, self._max_steps + 1):
                resp = await self._gemini.generate_with_tools(
                    contents=contents,
                    tools=tool_decls,
                    system_instruction=system_instruction,
                    enable_google_search=enable_google_search,
                )

                if resp.tool_calls:
                    # Append the raw assistant Content (carries thought_signature
                    # required by Gemini for follow-up calls within this turn).
                    if resp.assistant_content is not None:
                        contents.append(resp.assistant_content)

                    for call in resp.tool_calls:
                        yield LoopEvent(
                            kind="assistant_tool_call",
                            step=step,
                            tool_call_id=call.id,
                            tool_name=call.name,
                            tool_args=call.args,
                        )

                        result = await self._dispatch(call.name, call.args)
                        yield LoopEvent(
                            kind="tool_result",
                            step=step,
                            tool_call_id=call.id,
                            tool_name=call.name,
                            tool_result=result,
                        )
                        contents.append(
                            genai_types.Content(
                                role="user",
                                parts=[
                                    genai_types.Part(
                                        function_response=genai_types.FunctionResponse(
                                            id=call.id,
                                            name=call.name,
                                            response=result,
                                        )
                                    )
                                ],
                            )
                        )
                    continue

                yield LoopEvent(
                    kind="assistant",
                    step=step,
                    text=resp.text or "",
                    citations=resp.citations,
                )
                return

            raise AgentLoopExceededError(
                f"agent loop exceeded {self._max_steps} steps without final answer"
            )

        # Per-turn wall-clock guard around the whole generator.
        try:
            async for event in _with_timeout(_runner(), self._per_turn_timeout_s):
                yield event
        except TimeoutError as exc:
            raise AgentLoopExceededError(
                f"agent loop exceeded per-turn timeout of {self._per_turn_timeout_s}s"
            ) from exc

    async def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"unknown tool {name!r}"}
        try:
            parsed = tool.args_schema.model_validate(args)
        except Exception as exc:
            return {"error": f"invalid args for {name}: {exc}"}
        try:
            return await asyncio.wait_for(
                tool.run(parsed, self._ctx), timeout=self._per_tool_timeout_s
            )
        except TimeoutError:
            return {"error": f"tool {name} exceeded {self._per_tool_timeout_s}s"}


def _tool_to_decl(tool: Tool) -> FunctionDecl:
    return FunctionDecl(
        name=tool.name,
        description=tool.description,
        parameters_json_schema=tool.args_schema.model_json_schema(),
    )


def _to_gemini_contents(history: list[HistoryMessage]) -> list[genai_types.Content]:
    """Convert prior persisted messages into Gemini Content for cross-turn replay.

    Only user text and assistant text are preserved. Prior function_call /
    function_response pairs are intentionally dropped — Gemini requires a
    `thought_signature` on function_call parts that we don't persist, and the
    prior assistant text already summarises the result of those calls.
    """
    out: list[genai_types.Content] = []
    for m in history:
        if m.role == "user" and m.content is not None:
            out.append(
                genai_types.Content(role="user", parts=[genai_types.Part(text=m.content)])
            )
        elif m.role == "assistant" and m.content is not None:
            out.append(
                genai_types.Content(role="model", parts=[genai_types.Part(text=m.content)])
            )
    return out


async def _with_timeout(
    aiter: AsyncIterator[LoopEvent], timeout_s: float
) -> AsyncIterator[LoopEvent]:
    """Yield items from `aiter` with a single shared deadline. Raises
    asyncio.TimeoutError if the total time exceeds `timeout_s`."""
    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise TimeoutError
        try:
            event = await asyncio.wait_for(aiter.__anext__(), timeout=remaining)
        except StopAsyncIteration:
            return
        yield event
