"""reports pipeline schema

Revision ID: 0001_reports_pipeline
Revises:
Create Date: 2026-04-27

Five tables for the report-crawl pipeline:
- sources, report_types: extensible source/type catalogue
- reports: main row, idempotent on (source_id, external_id)
- report_extractions: per-(report, prompt_version) LLM outputs
- crawl_runs: per-invocation observability log
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_reports_pipeline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("base_url", sa.String(256)),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "report_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("ticker_indexed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("extraction_schema", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("source_id", "external_id", name="uq_report_types_source_external"),
    )

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("report_type_id", sa.Integer(), sa.ForeignKey("report_types.id"), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("ticker", sa.String(16)),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("publisher", sa.String(128)),
        sa.Column("published_at", sa.Date()),
        sa.Column("detail_url", sa.Text()),
        sa.Column("pdf_url", sa.Text()),
        sa.Column("pdf_object_key", sa.Text()),
        sa.Column("pdf_sha256", sa.CHAR(64)),
        sa.Column("pdf_size_bytes", sa.Integer()),
        sa.Column("status", sa.String(32), nullable=False, server_default="discovered"),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("downloaded_at", sa.DateTime(timezone=True)),
        sa.Column("extracted_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_reports_source_external"),
    )
    op.create_index("ix_reports_source_id", "reports", ["source_id"])
    op.create_index("ix_reports_report_type_id", "reports", ["report_type_id"])
    op.create_index("ix_reports_ticker", "reports", ["ticker"])
    op.create_index("ix_reports_published_at", "reports", ["published_at"])
    op.create_index("ix_reports_pdf_sha256", "reports", ["pdf_sha256"])
    op.create_index("ix_reports_status", "reports", ["status"])

    op.create_table(
        "report_extractions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(32), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("summary", sa.Text()),
        sa.Column("recommendation", sa.String(32)),
        sa.Column("target_price", sa.Numeric(18, 2)),
        sa.Column("target_currency", sa.String(8)),
        sa.Column("horizon", sa.String(32)),
        sa.Column("extras", postgresql.JSONB()),
        sa.Column("raw_response", postgresql.JSONB()),
        sa.UniqueConstraint("report_id", "prompt_version", name="uq_extractions_report_prompt"),
    )

    op.create_table(
        "crawl_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("report_type_id", sa.Integer(), sa.ForeignKey("report_types.id")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("downloaded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extracted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("crawl_runs")
    op.drop_table("report_extractions")
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_index("ix_reports_pdf_sha256", table_name="reports")
    op.drop_index("ix_reports_published_at", table_name="reports")
    op.drop_index("ix_reports_ticker", table_name="reports")
    op.drop_index("ix_reports_report_type_id", table_name="reports")
    op.drop_index("ix_reports_source_id", table_name="reports")
    op.drop_table("reports")
    op.drop_table("report_types")
    op.drop_table("sources")
