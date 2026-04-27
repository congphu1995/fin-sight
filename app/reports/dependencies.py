# reports-feature wiring; depends on app/dependencies.py for shared infra.
"""Feature-local DI helpers.

The orchestration layer (jobs.py / __main__.py) constructs sources and services
through these helpers. They are NOT FastAPI dependencies — the API surface uses
the standard get_session pattern from app.dependencies.
"""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.reports.crawlers.base import SOURCE_REGISTRY, ReportSource


def make_http_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={
            "User-Agent": settings.crawl_user_agent,
            "Accept-Language": "vi,en;q=0.8",
        },
        timeout=20.0,
        follow_redirects=True,
    )


def build_source(code: str, http: httpx.AsyncClient, settings: Settings) -> ReportSource:
    cls = SOURCE_REGISTRY.get(code)
    if cls is None:
        raise RuntimeError(
            f"unknown source code {code!r}; "
            f"registered: {sorted(SOURCE_REGISTRY)}"
        )
    return cls(http=http, request_delay_seconds=settings.crawl_request_delay_seconds)
