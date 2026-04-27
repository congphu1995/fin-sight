"""Read-only HTTP endpoints over the reports tables."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage.minio_client import MinioClient
from app.dependencies import get_minio_client, get_session
from app.reports.models import Report, ReportExtraction, ReportType, Source
from app.reports.schemas import ExtractionOut, ReportDetail, ReportOut

router = APIRouter(tags=["reports"])


@router.get("/reports", response_model=list[ReportOut])
async def list_reports(
    session: Annotated[AsyncSession, Depends(get_session)],
    source: str | None = None,
    type_id: str | None = Query(default=None, alias="type"),
    ticker: str | None = None,
    status: str | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ReportOut]:
    stmt = (
        select(Report, Source.code, ReportType.external_id)
        .join(Source, Source.id == Report.source_id)
        .join(ReportType, ReportType.id == Report.report_type_id)
    )
    if source:
        stmt = stmt.where(Source.code == source)
    if type_id:
        stmt = stmt.where(ReportType.external_id == type_id)
    if ticker:
        stmt = stmt.where(Report.ticker == ticker.upper())
    if status:
        stmt = stmt.where(Report.status == status)
    stmt = (
        stmt.order_by(Report.published_at.desc().nulls_last(), Report.discovered_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).all()
    return [_to_report_out(r, src_code, rtype_ext) for (r, src_code, rtype_ext) in rows]


@router.get("/reports/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReportDetail:
    row = (
        await session.execute(
            select(Report, Source.code, ReportType.external_id)
            .join(Source, Source.id == Report.source_id)
            .join(ReportType, ReportType.id == Report.report_type_id)
            .where(Report.id == report_id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")
    report, src_code, rtype_ext = row

    latest = (
        await session.execute(
            select(ReportExtraction)
            .where(ReportExtraction.report_id == report_id)
            .order_by(ReportExtraction.extracted_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    return ReportDetail(
        report=_to_report_out(report, src_code, rtype_ext),
        latest_extraction=_to_extraction_out(latest) if latest else None,
    )


@router.get("/reports/{report_id}/pdf")
async def get_report_pdf(
    report_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    minio: Annotated[MinioClient, Depends(get_minio_client)],
) -> RedirectResponse:
    report = (
        await session.execute(select(Report).where(Report.id == report_id))
    ).scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.pdf_object_key:
        raise HTTPException(status_code=404, detail="PDF not yet downloaded")
    url = await minio.presigned_get_url(report.pdf_object_key, expires_seconds=900)
    return RedirectResponse(url=url, status_code=302)


def _to_report_out(report: Report, source_code: str, type_external_id: str) -> ReportOut:
    return ReportOut(
        id=report.id,
        source_code=source_code,
        report_type_external_id=type_external_id,
        external_id=report.external_id,
        ticker=report.ticker,
        title=report.title,
        publisher=report.publisher,
        published_at=report.published_at,
        detail_url=report.detail_url,
        pdf_url=report.pdf_url,
        status=report.status,
        discovered_at=report.discovered_at,
        downloaded_at=report.downloaded_at,
        extracted_at=report.extracted_at,
    )


def _to_extraction_out(e: ReportExtraction) -> ExtractionOut:
    return ExtractionOut(
        id=e.id,
        report_id=e.report_id,
        model=e.model,
        prompt_version=e.prompt_version,
        extracted_at=e.extracted_at,
        summary=e.summary,
        recommendation=e.recommendation,
        target_price=e.target_price,
        target_currency=e.target_currency,
        horizon=e.horizon,
        extras=e.extras or {},
    )
