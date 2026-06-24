"""Gemini access for the reports pipeline.

Two responsibilities only, both PDF-centric:
  - `generate_from_pdf` — structured extraction (PDF + prompt → Pydantic schema).
  - `ask_about_pdf`     — free-text Q&A over a PDF (the `ask_report_pdf` tool).

(The former tool-calling / agent-loop path was removed when fin-sight became a
headless MCP backend — the agent now lives in Mira, not here.)
"""

from typing import TypeVar

from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel

from app.core.exceptions import LLMError

T = TypeVar("T", bound=BaseModel)


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

    async def ask_about_pdf(self, pdf_bytes: bytes, query: str) -> str:
        """Free-text Q&A over a PDF — used by the `ask_report_pdf` tool.

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
