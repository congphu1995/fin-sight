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
