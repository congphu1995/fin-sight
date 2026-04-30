"""Unit tests for AgentLoop.

The loop is purely orchestration — gemini calls + tool dispatch + bounds. We
script gemini responses with FakeGeminiClient and provide a fake tool that
echoes its args. No DB, no FastAPI.
"""

import asyncio
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field

from app.agent.runtime.loop import AgentLoop, HistoryMessage, LoopEvent
from app.agent.tools.base import Tool, ToolContext
from app.core.exceptions import AgentLoopExceededError
from tests.base import FakeGeminiClient


class EchoArgs(BaseModel):
    text: str = Field(..., description="anything")


class EchoTool(Tool):
    name = "echo"
    description = "echo input"
    args_schema = EchoArgs

    def __init__(self, delay_s: float = 0.0) -> None:
        self.delay_s = delay_s
        self.calls: list[EchoArgs] = []

    async def run(self, args: EchoArgs, ctx: ToolContext) -> dict:
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        self.calls.append(args)
        return {"echoed": args.text}


def _ctx() -> ToolContext:
    return ToolContext(
        session=MagicMock(),
        minio=MagicMock(),
        gemini=MagicMock(),
        logger=MagicMock(),
    )


async def _drain(aiter) -> list[LoopEvent]:
    return [ev async for ev in aiter]


async def test_single_text_response_yields_user_then_assistant() -> None:
    fake = FakeGeminiClient()
    fake.script_text("hello there")
    loop = AgentLoop(fake, tools={"echo": EchoTool()}, ctx=_ctx())

    events = await _drain(loop.run_turn(prior=[], user_text="hi"))

    assert [e.kind for e in events] == ["user", "assistant"]
    assert events[0].text == "hi"
    assert events[1].text == "hello there"


async def test_tool_call_then_final_text() -> None:
    fake = FakeGeminiClient()
    fake.script_tool_call("echo", {"text": "ping"})
    fake.script_text("done")
    echo = EchoTool()
    loop = AgentLoop(fake, tools={"echo": echo}, ctx=_ctx())

    events = await _drain(loop.run_turn(prior=[], user_text="please echo"))

    assert [e.kind for e in events] == ["user", "assistant_tool_call", "tool_result", "assistant"]
    assert events[1].tool_name == "echo"
    assert events[1].tool_args == {"text": "ping"}
    assert events[2].tool_result == {"echoed": "ping"}
    assert events[3].text == "done"
    assert echo.calls and echo.calls[0].text == "ping"


async def test_unknown_tool_returns_error_then_loop_continues() -> None:
    fake = FakeGeminiClient()
    fake.script_tool_call("does_not_exist", {})
    fake.script_text("recovered")
    loop = AgentLoop(fake, tools={"echo": EchoTool()}, ctx=_ctx())

    events = await _drain(loop.run_turn(prior=[], user_text="x"))

    tool_result = next(e for e in events if e.kind == "tool_result")
    assert "unknown tool" in tool_result.tool_result["error"]
    assert events[-1].text == "recovered"


async def test_invalid_args_returned_as_error_not_raised() -> None:
    fake = FakeGeminiClient()
    fake.script_tool_call("echo", {"wrong_field": "x"})
    fake.script_text("ok")
    loop = AgentLoop(fake, tools={"echo": EchoTool()}, ctx=_ctx())

    events = await _drain(loop.run_turn(prior=[], user_text="x"))

    tool_result = next(e for e in events if e.kind == "tool_result")
    assert "invalid args" in tool_result.tool_result["error"]


async def test_max_steps_exceeded_raises() -> None:
    fake = FakeGeminiClient()
    # Always respond with a tool call — will spin until MAX_STEPS.
    for _ in range(20):
        fake.script_tool_call("echo", {"text": "x"})
    loop = AgentLoop(fake, tools={"echo": EchoTool()}, ctx=_ctx(), max_steps=3)

    with pytest.raises(AgentLoopExceededError):
        await _drain(loop.run_turn(prior=[], user_text="x"))


async def test_per_tool_timeout() -> None:
    fake = FakeGeminiClient()
    fake.script_tool_call("echo", {"text": "ping"})
    fake.script_text("done")
    slow = EchoTool(delay_s=0.5)
    loop = AgentLoop(
        fake, tools={"echo": slow}, ctx=_ctx(), per_tool_timeout_s=0.05
    )

    events = await _drain(loop.run_turn(prior=[], user_text="x"))
    tool_result = next(e for e in events if e.kind == "tool_result")
    assert "exceeded" in tool_result.tool_result["error"]


async def test_prior_history_is_included_in_first_call() -> None:
    fake = FakeGeminiClient()
    fake.script_text("answer")
    prior = [
        HistoryMessage(role="user", content="earlier"),
        HistoryMessage(role="assistant", content="earlier reply"),
    ]
    loop = AgentLoop(fake, tools={}, ctx=_ctx())

    await _drain(loop.run_turn(prior=prior, user_text="now"))

    contents = fake.tool_calls_log[0]["contents"]
    # 2 prior + 1 current user message
    assert len(contents) == 3
