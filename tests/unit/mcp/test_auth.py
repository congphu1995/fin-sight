"""The bearer middleware guards the MCP prefix and leaves other routes open."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.mcp.auth import BearerAuthMiddleware


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/mcp/ping")
    async def mcp_ping() -> dict:
        return {"ok": True}

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True}

    app.add_middleware(BearerAuthMiddleware, token="secret", path_prefix="/mcp")
    return app


async def test_guards_mcp_prefix() -> None:
    async with AsyncClient(transport=ASGITransport(app=_app()), base_url="http://t") as ac:
        assert (await ac.get("/mcp/ping")).status_code == 401
        assert (
            await ac.get("/mcp/ping", headers={"Authorization": "Bearer wrong"})
        ).status_code == 401
        ok = await ac.get("/mcp/ping", headers={"Authorization": "Bearer secret"})
        assert ok.status_code == 200 and ok.json() == {"ok": True}


async def test_leaves_other_routes_open() -> None:
    async with AsyncClient(transport=ASGITransport(app=_app()), base_url="http://t") as ac:
        assert (await ac.get("/healthz")).status_code == 200
