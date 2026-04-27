from google import genai

from app.core.exceptions import LLMError


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
