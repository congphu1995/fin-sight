"""Stage 1: discover reports via a ReportSource and upsert them.

Idempotent on (source_id, external_id): existing rows are not touched.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.reports.crawlers.base import DiscoveredReport, ReportSource
from app.reports.models import Report, ReportType, Source


class CrawlerService:
    def __init__(
        self,
        session: AsyncSession,
        source_obj: Source,
        report_type: ReportType,
        crawler: ReportSource,
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        self._session = session
        self._source = source_obj
        self._report_type = report_type
        self._crawler = crawler
        self._logger = logger

    async def discover(
        self,
        *,
        since,
        until,
        ticker: str | None = None,
    ) -> int:
        """Upsert all discovered reports. Returns count of newly-inserted rows."""
        self._logger.info(
            "crawler.discover.start",
            source=self._source.code,
            report_type=self._report_type.external_id,
            since=since.isoformat(),
            until=until.isoformat(),
            ticker=ticker,
        )

        inserted = 0
        async for found in self._crawler.discover(
            self._report_type.external_id, since, until, ticker=ticker
        ):
            if await self._upsert(found):
                inserted += 1

        await self._session.commit()
        self._logger.info(
            "crawler.discover.done",
            source=self._source.code,
            report_type=self._report_type.external_id,
            inserted=inserted,
        )
        return inserted

    async def _upsert(self, found: DiscoveredReport) -> bool:
        """Insert if (source_id, external_id) is new; otherwise no-op. Returns True if inserted."""
        stmt = (
            pg_insert(Report)
            .values(
                source_id=self._source.id,
                report_type_id=self._report_type.id,
                external_id=found.external_id,
                ticker=found.ticker,
                title=found.title,
                publisher=found.publisher,
                published_at=found.published_at,
                detail_url=found.detail_url,
                pdf_url=found.pdf_url,
                status="discovered",
            )
            .on_conflict_do_nothing(index_elements=["source_id", "external_id"])
            .returning(Report.id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None


async def get_source(session: AsyncSession, code: str) -> Source | None:
    return (await session.execute(select(Source).where(Source.code == code))).scalar_one_or_none()


async def get_report_type(
    session: AsyncSession, source_id: int, external_id: str
) -> ReportType | None:
    return (
        await session.execute(
            select(ReportType).where(
                ReportType.source_id == source_id,
                ReportType.external_id == external_id,
            )
        )
    ).scalar_one_or_none()


async def list_enabled_types(session: AsyncSession, source_id: int) -> list[ReportType]:
    result = await session.execute(
        select(ReportType).where(ReportType.source_id == source_id, ReportType.enabled.is_(True))
    )
    return list(result.scalars().all())


async def list_enabled_sources(session: AsyncSession) -> list[Source]:
    result = await session.execute(select(Source).where(Source.enabled.is_(True)))
    return list(result.scalars().all())
