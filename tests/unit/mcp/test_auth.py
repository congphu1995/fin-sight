"""The bearer middleware guards routes with a static token."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.mcp.auth import BearerAuthMiddleware


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    async def ping() -> dict:
        return {"ok": True}

    app.add_middleware(BearerAuthMiddleware, token="secret")
    return app


async def test_rejects_missing_and_wrong_token() -> None:
    async with AsyncClient(transport=ASGITransport(app=_app()), base_url="http://t") as ac:
        assert (await ac.get("/ping")).status_code == 401
        assert (await ac.get("/ping", headers={"Authorization": "Bearer wrong"})).status_code == 401


async def test_allows_correct_token() -> None:
    async with AsyncClient(transport=ASGITransport(app=_app()), base_url="http://t") as ac:
        r = await ac.get("/ping", headers={"Authorization": "Bearer secret"})
        assert r.status_code == 200 and r.json() == {"ok": True}
