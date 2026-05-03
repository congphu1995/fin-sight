"""initial schema: reports pipeline, agent layer, extraction facets, vietstock seed

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-03

Single consolidated migration. Tables created in dependency order:

  sources, report_types, reports, report_extractions, crawl_runs,
  conversations, messages.

`report_extractions` includes the 5 facet columns (industry_name, topic,
outlook, period, mentioned_tickers) and their indexes from the start. The
Vietstock source + 5 report_types rows are seeded at the end of upgrade()
using the universal-slug `code` values that the runtime speaks.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


VIETSTOCK_TYPES = [
    # code, name, ticker_indexed
    ("technical", "Vietstock: Nghiên cứu - Phân tích", False),
    ("macro",     "Vĩ mô - Chiến lược thị trường",     False),
    ("industry",  "Phân tích ngành",                   False),
    ("company",   "Phân tích doanh nghiệp",            True),
    ("thematic",  "Báo cáo Chuyên đề",                 False),
]


def upgrade() -> None:
    # --- sources -------------------------------------------------------------
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("base_url", sa.String(256)),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- report_types --------------------------------------------------------
    # `code` is the universal slug ('company', 'industry', ...) the public
    # surface (CLI, API, logs, EXTRACTION_REGISTRY) speaks. Source-specific
    # ID mappings (e.g. Vietstock's '58') live on the crawler class.
    op.create_table(
        "report_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("ticker_indexed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("source_id", "code", name="uq_report_types_source_code"),
    )

    # --- reports -------------------------------------------------------------
    op.create_table(
        "reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column(
            "report_type_id", sa.Integer(), sa.ForeignKey("report_types.id"), nullable=False
        ),
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
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
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

    # --- report_extractions --------------------------------------------------
    # Includes the 5 facet columns + check constraint + indexes from the start.
    op.create_table(
        "report_extractions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(32), nullable=False),
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("summary", sa.Text()),
        sa.Column("recommendation", sa.String(32)),
        sa.Column("target_price", sa.Numeric(18, 2)),
        sa.Column("target_currency", sa.String(8)),
        sa.Column("horizon", sa.String(32)),
        sa.Column("extras", postgresql.JSONB()),
        sa.Column("raw_response", postgresql.JSONB()),
        # Facet columns — derived from the type-specific schema by
        # ExtractorService._extract_facets. NULL when the source schema
        # doesn't have the corresponding field.
        sa.Column("industry_name", sa.String(128), nullable=True),
        sa.Column("topic", sa.String(256), nullable=True),
        sa.Column("outlook", sa.String(16), nullable=True),
        sa.Column("period", sa.String(64), nullable=True),
        sa.Column(
            "mentioned_tickers", postgresql.ARRAY(sa.String(16)), nullable=True
        ),
        sa.UniqueConstraint(
            "report_id", "prompt_version", name="uq_extractions_report_prompt"
        ),
        sa.CheckConstraint(
            "outlook IS NULL OR outlook IN ('POSITIVE','NEUTRAL','NEGATIVE')",
            name="ck_extractions_outlook",
        ),
    )
    op.create_index(
        "ix_report_extractions_industry_name", "report_extractions", ["industry_name"]
    )
    op.create_index("ix_report_extractions_topic", "report_extractions", ["topic"])
    op.create_index("ix_report_extractions_outlook", "report_extractions", ["outlook"])
    op.create_index(
        "ix_report_extractions_mentioned_tickers",
        "report_extractions",
        ["mentioned_tickers"],
        postgresql_using="gin",
    )

    # --- crawl_runs ----------------------------------------------------------
    op.create_table(
        "crawl_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("report_type_id", sa.Integer(), sa.ForeignKey("report_types.id")),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("downloaded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extracted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text()),
    )

    # --- conversations + messages (agent layer) ------------------------------
    op.create_table(
        "conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("agent_key", sa.String(64), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_conversations_agent_key", "conversations", ["agent_key"])

    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("tool_call_id", sa.String(128)),
        sa.Column("tool_name", sa.String(64)),
        sa.Column("tool_args", postgresql.JSONB()),
        sa.Column("tool_result", postgresql.JSONB()),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_messages_conversation_created",
        "messages",
        ["conversation_id", "created_at"],
    )

    # --- seed: vietstock source + 5 report types ----------------------------
    sources = sa.table(
        "sources",
        sa.column("id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("base_url", sa.String),
        sa.column("enabled", sa.Boolean),
    )
    op.bulk_insert(
        sources,
        [
            {
                "code": "vietstock",
                "name": "Vietstock",
                "base_url": "https://finance.vietstock.vn",
                "enabled": True,
            }
        ],
    )

    bind = op.get_bind()
    source_id = bind.execute(
        sa.text("SELECT id FROM sources WHERE code = 'vietstock'")
    ).scalar_one()

    report_types = sa.table(
        "report_types",
        sa.column("source_id", sa.Integer),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("ticker_indexed", sa.Boolean),
        sa.column("enabled", sa.Boolean),
    )
    op.bulk_insert(
        report_types,
        [
            {
                "source_id": source_id,
                "code": code,
                "name": name,
                "ticker_indexed": ticker_indexed,
                "enabled": True,
            }
            for code, name, ticker_indexed in VIETSTOCK_TYPES
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_agent_key", table_name="conversations")
    op.drop_table("conversations")

    op.drop_table("crawl_runs")

    op.drop_index(
        "ix_report_extractions_mentioned_tickers", table_name="report_extractions"
    )
    op.drop_index("ix_report_extractions_outlook", table_name="report_extractions")
    op.drop_index("ix_report_extractions_topic", table_name="report_extractions")
    op.drop_index(
        "ix_report_extractions_industry_name", table_name="report_extractions"
    )
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
