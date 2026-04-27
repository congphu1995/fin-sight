import os
from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient

# Set safe defaults BEFORE importing the app, so Settings doesn't load real .env values.
os.environ.setdefault("ENV", "dev")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-flash-lite-latest")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test")
os.environ.setdefault("MINIO_BUCKET", "test-bucket")
os.environ.setdefault("MINIO_SECURE", "false")

from app.dependencies import get_gemini  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from tests.base import FakeGeminiClient  # noqa: E402


@pytest.fixture
def fake_gemini() -> FakeGeminiClient:
    return FakeGeminiClient()


@pytest.fixture
def app(fake_gemini: FakeGeminiClient) -> Iterator[object]:
    fastapi_app.dependency_overrides[get_gemini] = lambda: fake_gemini
    try:
        yield fastapi_app
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.fixture
async def client(app: object) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as ac:
        yield ac
