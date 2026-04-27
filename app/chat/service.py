import structlog

from app.core.llm.gemini import GeminiClient


class ChatService:
    def __init__(self, gemini: GeminiClient, logger: structlog.stdlib.BoundLogger) -> None:
        self._gemini = gemini
        self._logger = logger

    async def answer(self, prompt: str) -> str:
        self._logger.info("chat.answer.start", prompt_length=len(prompt))
        answer = await self._gemini.generate(prompt)
        self._logger.info("chat.answer.done", answer_length=len(answer))
        return answer
