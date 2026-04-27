from httpx import AsyncClient

from tests.base import FakeGeminiClient


async def test_chat_returns_fake_answer(
    client: AsyncClient, fake_gemini: FakeGeminiClient
) -> None:
    fake_gemini.answer = "hello-from-fake"

    resp = await client.post("/api/v1/chat", json={"prompt": "hi"})

    assert resp.status_code == 200
    assert resp.json() == {"answer": "hello-from-fake"}
    assert fake_gemini.prompts == ["hi"]


async def test_chat_rejects_empty_prompt(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/chat", json={"prompt": ""})
    assert resp.status_code == 422
