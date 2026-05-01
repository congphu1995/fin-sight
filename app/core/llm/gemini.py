from dataclasses import dataclass, field
from typing import Any, TypeVar

from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel

from app.core.exceptions import LLMError

T = TypeVar("T", bound=BaseModel)


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class ToolUseResponse:
    """Result of a tool-enabled generate call.

    Either `tool_calls` is non-empty (the model wants to invoke tools) OR
    `text` is set (the model produced a final answer). The agent loop branches
    on this distinction.

    `assistant_content` is the raw `Content` object Gemini returned. The agent
    loop appends it verbatim to the next request's `contents` list — necessary
    because function_call parts carry a `thought_signature` that Gemini
    rejects when re-sent without it.
    """

    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    assistant_content: Any = None


@dataclass
class FunctionDecl:
    """Lightweight function declaration. We accept this shape rather than
    the SDK's FunctionDeclaration so callers don't have to import google.genai."""

    name: str
    description: str
    parameters_json_schema: dict[str, Any]


def _parse_tool_use_response(response: Any) -> ToolUseResponse:
    """Extract tool calls, text, and grounding citations from a Gemini response.

    Function calls live as `function_call` parts on the first candidate's
    content. Text parts are concatenated. We generate a stable id per call so
    the agent loop can link a tool result back to its assistant call when
    multiple tool_calls come in one turn.
    """
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return ToolUseResponse(text=None)

    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) or [] if content else []

    tool_calls: list[ToolCall] = []
    text_chunks: list[str] = []
    for idx, part in enumerate(parts):
        fn = getattr(part, "function_call", None)
        if fn is not None:
            args = getattr(fn, "args", None) or {}
            if not isinstance(args, dict):
                args = dict(args)
            call_id = getattr(fn, "id", None) or f"call_{idx}"
            tool_calls.append(ToolCall(id=call_id, name=fn.name, args=args))
            continue
        text = getattr(part, "text", None)
        if text:
            text_chunks.append(text)

    citations: list[dict[str, Any]] = []
    grounding = getattr(candidates[0], "grounding_metadata", None)
    if grounding is not None:
        for chunk in getattr(grounding, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            if web is not None:
                citations.append(
                    {"uri": getattr(web, "uri", None), "title": getattr(web, "title", None)}
                )

    return ToolUseResponse(
        text="".join(text_chunks) if text_chunks and not tool_calls else None,
        tool_calls=tool_calls,
        citations=citations,
        assistant_content=content,
    )


def _strip_additional_properties(schema: dict[str, Any]) -> dict[str, Any]:
    """Gemini's structured output / function calling rejects `additionalProperties`.

    Pydantic emits it on `dict[...]` fields. Walk the schema and drop the key
    everywhere. (See CLAUDE.md → Gotchas.)
    """
    if not isinstance(schema, dict):
        return schema
    out: dict[str, Any] = {}
    for k, v in schema.items():
        if k == "additionalProperties":
            continue
        if isinstance(v, dict):
            out[k] = _strip_additional_properties(v)
        elif isinstance(v, list):
            out[k] = [_strip_additional_properties(x) if isinstance(x, dict) else x for x in v]
        else:
            out[k] = v
    return out


class GeminiClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = genai.Client(api_key=api_key)

    async def generate(self, prompt: str) -> str:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
            )
        except Exception as exc:
            raise LLMError(str(exc)) from exc

        text = getattr(response, "text", None)
        if not text:
            raise LLMError("Empty response from Gemini")
        return text

    async def generate_with_tools(
        self,
        contents: list[genai_types.Content],
        tools: list[FunctionDecl],
        *,
        system_instruction: str | None = None,
        enable_google_search: bool = False,
    ) -> ToolUseResponse:
        """Single-turn LLM call with function-calling enabled.

        The caller (agent loop) is responsible for the tool-dispatch loop:
        on a `tool_calls` response it executes each tool, appends the
        results to `contents`, and calls again until a final `text` response.
        Automatic function calling is disabled — we handle the loop ourselves.
        """
        sdk_tools: list[genai_types.Tool] = []
        if tools:
            sdk_tools.append(
                genai_types.Tool(
                    function_declarations=[
                        genai_types.FunctionDeclaration(
                            name=t.name,
                            description=t.description,
                            parameters_json_schema=_strip_additional_properties(
                                t.parameters_json_schema
                            ),
                        )
                        for t in tools
                    ]
                )
            )
        if enable_google_search:
            sdk_tools.append(genai_types.Tool(google_search=genai_types.GoogleSearch()))

        config = genai_types.GenerateContentConfig(
            tools=sdk_tools or None,
            system_instruction=system_instruction,
            automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(disable=True),
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            raise LLMError(str(exc)) from exc

        return _parse_tool_use_response(response)

    async def ask_about_pdf(self, pdf_bytes: bytes, query: str) -> str:
        """Free-text Q&A over a PDF — used by the chat agent's `ask_report_pdf` tool.

        Differs from `generate_from_pdf` in that there's no Pydantic schema:
        Gemini returns a plain-text answer scoped to whatever the query asks.
        """
        pdf_part = genai_types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[pdf_part, query],
            )
        except Exception as exc:
            raise LLMError(str(exc)) from exc

        text = getattr(response, "text", None)
        if not text:
            raise LLMError("Empty response from Gemini PDF Q&A call")
        return text

    async def generate_from_pdf(
        self,
        pdf_bytes: bytes,
        prompt: str,
        response_schema: type[T],
    ) -> T:
        """Send a PDF + prompt to Gemini, parse response as response_schema."""
        pdf_part = genai_types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=[pdf_part, prompt],
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )
        except Exception as exc:
            raise LLMError(str(exc)) from exc

        parsed = getattr(response, "parsed", None)
        if parsed is None:
            text = getattr(response, "text", None)
            if not text:
                raise LLMError("Empty response from Gemini PDF call")
            try:
                parsed = response_schema.model_validate_json(text)
            except Exception as exc:
                raise LLMError(
                    f"Could not parse Gemini response as {response_schema.__name__}: {exc}"
                ) from exc
        return parsed
