"""API DTOs for the reports endpoints."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ReportOut(BaseModel):
    id: UUID
    source_code: str
    report_type_code: str
    external_id: str
    ticker: str | None = None
    title: str
    publisher: str | None = None
    published_at: date | None = None
    detail_url: str | None = None
    pdf_url: str | None = None
    status: str
    discovered_at: datetime
    downloaded_at: datetime | None = None
    extracted_at: datetime | None = None


class ExtractionOut(BaseModel):
    id: UUID
    report_id: UUID
    model: str
    prompt_version: str
    extracted_at: datetime
    summary: str | None = None
    recommendation: str | None = None
    target_price: Decimal | None = None
    target_currency: str | None = None
    horizon: str | None = None
    extras: dict[str, Any] = Field(default_factory=dict)


class ReportDetail(BaseModel):
    report: ReportOut
    latest_extraction: ExtractionOut | None = None
