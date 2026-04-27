from httpx import AsyncClient


async def test_request_id_echoed_when_provided(client: AsyncClient) -> None:
    custom = "client-supplied-id-123"
    resp = await client.get("/api/v1/health", headers={"X-Request-ID": custom})
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] == custom


async def test_request_id_generated_when_absent(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"]
