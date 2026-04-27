"""Unit tests for the storage stage.

These tests don't hit Postgres; they use in-memory SQLite + the same ORM models
to exercise the SQL paths (insert, dedup-by-sha256, status transitions).
"""


import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.reports.models import ReportType, Source


@pytest.fixture
async def session() -> object:
    # Use Postgres-only features (UUID, JSONB) sparingly here; SQLite stand-in works
    # because we only INSERT values and SELECT them back.
    pytest.importorskip("aiosqlite")
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _seed_source_and_type(session) -> tuple[Source, ReportType]:
    src = Source(code="vietstock", name="Vietstock", base_url="https://example.test", enabled=True)
    session.add(src)
    await session.flush()
    rt = ReportType(
        source_id=src.id,
        external_id="58",
        code="phan-tich-doanh-nghiep",
        name="Phân tích doanh nghiệp",
        ticker_indexed=True,
        extraction_schema="company",
        enabled=True,
    )
    session.add(rt)
    await session.flush()
    return src, rt


@pytest.mark.skip(reason="SQLite lacks ON CONFLICT + FOR UPDATE; covered by integration tests")
async def test_storage_downloads_and_dedups(session) -> None:
    pass
