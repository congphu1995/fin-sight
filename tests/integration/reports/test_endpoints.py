"""Integration tests for the reports HTTP endpoints.

Heavy-DB tests (rows in Postgres, real SQL) are skipped by default — the full
end-to-end flow is exercised with `docker compose up && python -m app.reports`.
This file just verifies route wiring (registration, OpenAPI shape).
"""

from httpx import AsyncClient


async def test_reports_routes_registered_in_openapi(client: AsyncClient) -> None:
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/v1/reports" in paths
    assert "/api/v1/reports/{report_id}" in paths
    assert "/api/v1/reports/{report_id}/pdf" in paths
