"""Pipeline orchestration — library functions, no argparse, no print.

Three idempotent stages:
  1. discover  — populate `reports` rows (status='discovered')
  2. download  — fetch PDF, store in MinIO, status='downloaded'
  3. extract   — Gemini, structured output, status='extracted'

Each stage gates on `status` so re-runs are no-ops on already-processed rows.
A single CrawlRun row is inserted per (source, type) per invocation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.llm.gemini import GeminiClient
from app.core.storage.minio_client import MinioClientProtocol
from app.reports.crawlers.base import ReportSource
from app.reports.dependencies import build_source, make_http_client
from app.reports.models import CrawlRun, ReportType, Source
from app.reports.services.crawler import (
    CrawlerService,
    get_report_type,
    get_source,
    list_enabled_sources,
    list_enabled_types,
)
from app.reports.services.extractor import ExtractorService
from app.reports.services.storage import StorageService

Stage = Literal["discover", "download", "extract"]


@dataclass
class StageCounts:
    discovered: int = 0
    downloaded: int = 0
    extracted: int = 0


async def run_pipeline(
    *,
    session_factory,
    settings: Settings,
    minio: MinioClientProtocol,
    gemini: GeminiClient,
    source_code: str | None = None,
    type_code: str | None = None,
    ticker: str | None = None,
    backfill_days: int | None = None,
    stages: tuple[Stage, ...] = ("discover", "download", "extract"),
    logger: structlog.stdlib.BoundLogger | None = None,
) -> dict[tuple[str, str], StageCounts]:
    """Run the pipeline across selected (source, type) pairs.

    Returns a dict keyed by (source_code, report_type_code) → counts.
    """
    log = logger or structlog.get_logger()
    until = date.today()
    since = until - timedelta(days=backfill_days or settings.crawl_default_lookback_days)

    http = make_http_client(settings)
    results: dict[tuple[str, str], StageCounts] = {}
    try:
        async with session_factory() as session:
            sources = await _select_sources(session, source_code)
            for source in sources:
                crawler = build_source(source.code, http, settings)
                rtypes = await _select_types(session, source, type_code)
                for rtype in rtypes:
                    counts = await _run_one(
                        session=session,
                        settings=settings,
                        source=source,
                        report_type=rtype,
                        crawler=crawler,
                        minio=minio,
                        gemini=gemini,
                        since=since,
                        until=until,
                        ticker=ticker if rtype.ticker_indexed else None,
                        stages=stages,
                        logger=log,
                    )
                    results[(source.code, rtype.code)] = counts
    finally:
        await http.aclose()
    return results


async def _select_sources(session: AsyncSession, source_code: str | None) -> list[Source]:
    if source_code:
        s = await get_source(session, source_code)
        if s is None:
            raise RuntimeError(f"source {source_code!r} not in DB; run migrations or seed it")
        return [s]
    return await list_enabled_sources(session)


async def _select_types(
    session: AsyncSession, source: Source, type_code: str | None
) -> list[ReportType]:
    if type_code:
        t = await get_report_type(session, source.id, type_code)
        if t is None:
            raise RuntimeError(
                f"report type {type_code!r} not registered for source {source.code!r}"
            )
        return [t]
    return await list_enabled_types(session, source.id)


async def _run_one(
    *,
    session: AsyncSession,
    settings: Settings,
    source: Source,
    report_type: ReportType,
    crawler: ReportSource,
    minio: MinioClientProtocol,
    gemini: GeminiClient,
    since: date,
    until: date,
    ticker: str | None,
    stages: tuple[Stage, ...],
    logger: structlog.stdlib.BoundLogger,
) -> StageCounts:
    run = CrawlRun(
        source_id=source.id,
        report_type_id=report_type.id,
        status="running",
    )
    session.add(run)
    await session.flush()
    counts = StageCounts()

    try:
        if "discover" in stages:
            cs = CrawlerService(session, source, report_type, crawler, logger)
            counts.discovered = await cs.discover(since=since, until=until, ticker=ticker)

        if "download" in stages:
            ss = StorageService(session, minio, logger, max_retries=settings.crawl_max_retries)
            counts.downloaded = await ss.process_pending(
                source, report_type, crawler, batch_size=settings.crawl_batch_size
            )

        if "extract" in stages:
            es = ExtractorService(
                session,
                minio,
                gemini,
                model_name=settings.gemini_model,
                logger=logger,
                max_retries=settings.crawl_max_retries,
            )
            counts.extracted = await es.process_pending(
                source, report_type, batch_size=settings.crawl_batch_size
            )

        await session.execute(
            update(CrawlRun)
            .where(CrawlRun.id == run.id)
            .values(
                status="success",
                finished_at=datetime.now(UTC),
                discovered=counts.discovered,
                downloaded=counts.downloaded,
                extracted=counts.extracted,
            )
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        async with session_factory_from_session(session)() as fresh:
            await fresh.execute(
                update(CrawlRun)
                .where(CrawlRun.id == run.id)
                .values(
                    status="failed",
                    finished_at=datetime.now(UTC),
                    discovered=counts.discovered,
                    downloaded=counts.downloaded,
                    extracted=counts.extracted,
                    error=str(exc)[:1000],
                )
            )
            await fresh.commit()
        logger.exception("jobs.stage.failed", source=source.code, type=report_type.code)
        raise
    return counts


def session_factory_from_session(session: AsyncSession):
    """Tiny helper: get a fresh session factory from a bound session, used for the
    failure-bookkeeping path where the original session has been rolled back."""
    bind = session.bind
    from sqlalchemy.ext.asyncio import async_sessionmaker

    return async_sessionmaker(bind, expire_on_commit=False)
