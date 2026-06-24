"""Stage 2: download PDFs to MinIO.

Work query selects rows at status='discovered'. Each row: fetch PDF via the
source's `fetch_pdf`, sha256, put to MinIO at `{source}/{type_id}/{external_id}.pdf`,
flip to status='downloaded'. If the same sha256 exists on another row, mark as
'duplicate' (skips extraction).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CrawlerError, StorageError
from app.core.storage.minio_client import MinioClientProtocol
from app.reports.crawlers.base import DiscoveredReport, ReportSource
from app.reports.models import Report, ReportType, Source


class StorageService:
    def __init__(
        self,
        session: AsyncSession,
        minio: MinioClientProtocol,
        logger: structlog.stdlib.BoundLogger,
        max_retries: int = 3,
    ) -> None:
        self._session = session
        self._minio = minio
        self._logger = logger
        self._max_retries = max_retries

    async def process_pending(
        self,
        source: Source,
        report_type: ReportType | None,
        crawler: ReportSource,
        batch_size: int,
    ) -> int:
        """Download up to `batch_size` PDFs. Returns count of newly-downloaded rows."""
        rt_id = report_type.id if report_type else None
        rows = await self._claim_batch(source.id, rt_id, batch_size)
        if not rows:
            return 0

        downloaded = 0
        for report in rows:
            try:
                await self._download_one(report, crawler)
                downloaded += 1
            except (CrawlerError, StorageError) as exc:
                await self._mark_failure(report, str(exc))

        await self._session.commit()
        return downloaded

    async def _claim_batch(
        self,
        source_id: int,
        report_type_id: int | None,
        batch_size: int,
    ) -> list[Report]:
        stmt = select(Report).where(
            Report.source_id == source_id,
            Report.status == "discovered",
            Report.retry_count < self._max_retries,
        )
        if report_type_id is not None:
            stmt = stmt.where(Report.report_type_id == report_type_id)
        stmt = (
            stmt.order_by(Report.published_at.desc().nulls_last())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _download_one(self, report: Report, crawler: ReportSource) -> None:
        found = DiscoveredReport(
            source_code=crawler.code,
            type_code="",  # not needed for fetch_pdf
            external_id=report.external_id,
            ticker=report.ticker,
            title=report.title,
            publisher=report.publisher,
            published_at=report.published_at,
            detail_url=report.detail_url,
            pdf_url=report.pdf_url,
        )

        pdf_bytes = await crawler.fetch_pdf(found)
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()

        # Content dedup: if another row already has this sha256, mark as duplicate.
        existing = await self._session.execute(
            select(Report.id).where(Report.pdf_sha256 == sha256, Report.id != report.id)
        )
        if existing.scalar_one_or_none() is not None:
            await self._session.execute(
                update(Report)
                .where(Report.id == report.id)
                .values(
                    pdf_sha256=sha256,
                    pdf_size_bytes=len(pdf_bytes),
                    status="duplicate",
                    downloaded_at=datetime.now(UTC),
                )
            )
            self._logger.info(
                "storage.dedup",
                report_id=str(report.id),
                external_id=report.external_id,
                sha256=sha256,
            )
            return

        object_key = f"{crawler.code}/{report.report_type_id}/{report.external_id}.pdf"
        await self._minio.put_object(object_key, pdf_bytes, content_type="application/pdf")

        await self._session.execute(
            update(Report)
            .where(Report.id == report.id)
            .values(
                pdf_object_key=object_key,
                pdf_sha256=sha256,
                pdf_size_bytes=len(pdf_bytes),
                status="downloaded",
                downloaded_at=datetime.now(UTC),
                last_error=None,
            )
        )
        self._logger.info(
            "storage.downloaded",
            report_id=str(report.id),
            external_id=report.external_id,
            object_key=object_key,
            size_bytes=len(pdf_bytes),
        )

    async def _mark_failure(self, report: Report, error: str) -> None:
        new_retry = report.retry_count + 1
        new_status = "failed" if new_retry >= self._max_retries else report.status
        await self._session.execute(
            update(Report)
            .where(Report.id == report.id)
            .values(
                retry_count=new_retry,
                last_error=error[:1000],
                status=new_status,
            )
        )
        self._logger.warning(
            "storage.failure",
            report_id=str(report.id),
            external_id=report.external_id,
            retry_count=new_retry,
            terminal=new_status == "failed",
            error=error[:200],
        )


async def count_status(session: AsyncSession, source_id: int) -> dict[str, int]:
    """Useful for tests + observability."""
    result = await session.execute(
        select(Report.status, func.count(Report.id))
        .where(Report.source_id == source_id)
        .group_by(Report.status)
    )
    return {status: count for status, count in result.all()}
