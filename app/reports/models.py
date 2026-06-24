"""ORM models for the reports pipeline.

Five tightly-related tables — kept in one file while the count is small.
Split into a models/ package when this exceeds ~7 classes or any class
grows past ~100 lines.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(256))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReportType(Base):
    __tablename__ = "report_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    # Universal slug: 'company', 'industry', 'macro', ... — same meaning across sources.
    # Doubles as the EXTRACTION_REGISTRY key. Source-specific filter values
    # (e.g. Vietstock's '58') live inside the crawler class, not here.
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    ticker_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("source_id", "code", name="uq_report_types_source_code"),)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    report_type_id: Mapped[int] = mapped_column(
        ForeignKey("report_types.id"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(128))
    published_at: Mapped[date | None] = mapped_column(Date, index=True)
    detail_url: Mapped[str | None] = mapped_column(Text)
    pdf_url: Mapped[str | None] = mapped_column(Text)
    pdf_object_key: Mapped[str | None] = mapped_column(Text)
    pdf_sha256: Mapped[str | None] = mapped_column(CHAR(64), index=True)
    pdf_size_bytes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(32), default="discovered", nullable=False, index=True
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_reports_source_external"),
    )


class ReportExtraction(Base):
    __tablename__ = "report_extractions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    report_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(String(32))
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    target_currency: Mapped[str | None] = mapped_column(String(8))
    horizon: Mapped[str | None] = mapped_column(String(32))
    extras: Mapped[dict | None] = mapped_column(JSONB)
    raw_response: Mapped[dict | None] = mapped_column(JSONB)
    # Promoted facets — derived from the type-specific schema by ExtractorService._extract_facets.
    # NULL when the source schema doesn't have the corresponding field.
    industry_name: Mapped[str | None] = mapped_column(String(128), index=True)
    topic: Mapped[str | None] = mapped_column(String(256), index=True)
    outlook: Mapped[str | None] = mapped_column(String(16), index=True)
    period: Mapped[str | None] = mapped_column(String(64))
    mentioned_tickers: Mapped[list[str] | None] = mapped_column(ARRAY(String(16)))

    __table_args__ = (
        UniqueConstraint("report_id", "prompt_version", name="uq_extractions_report_prompt"),
        CheckConstraint(
            "outlook IS NULL OR outlook IN ('POSITIVE','NEUTRAL','NEGATIVE')",
            name="ck_extractions_outlook",
        ),
    )


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    report_type_id: Mapped[int | None] = mapped_column(ForeignKey("report_types.id"))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    downloaded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extracted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
