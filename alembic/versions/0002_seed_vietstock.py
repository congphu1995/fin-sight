"""seed vietstock source + 5 report types

Revision ID: 0002_seed_vietstock
Revises: 0001_reports_pipeline
Create Date: 2026-04-27

Seeds the catalog rows that map Vietstock's reportTypeID values to our
extraction schema keys. Adding a new type later is a new migration or
direct INSERT — the registry isn't hardcoded in Python.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_seed_vietstock"
down_revision: str | None = "0001_reports_pipeline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


VIETSTOCK_TYPES = [
    # external_id, code, name, ticker_indexed, extraction_schema
    ("49", "vietstock-nghien-cuu-phan-tich",  "Vietstock: Nghiên cứu - Phân tích",  False, "technical"),
    ("51", "vi-mo-chien-luoc-thi-truong",     "Vĩ mô - Chiến lược thị trường",      False, "macro"),
    ("57", "phan-tich-nganh",                  "Phân tích ngành",                    False, "industry"),
    ("58", "phan-tich-doanh-nghiep",           "Phân tích doanh nghiệp",             True,  "company"),
    ("59", "bao-cao-chuyen-de",                "Báo cáo Chuyên đề",                  False, "thematic"),
]


def upgrade() -> None:
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
            },
        ],
    )

    bind = op.get_bind()
    source_id = bind.execute(
        sa.text("SELECT id FROM sources WHERE code = 'vietstock'")
    ).scalar_one()

    report_types = sa.table(
        "report_types",
        sa.column("source_id", sa.Integer),
        sa.column("external_id", sa.String),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("ticker_indexed", sa.Boolean),
        sa.column("extraction_schema", sa.String),
        sa.column("enabled", sa.Boolean),
    )
    op.bulk_insert(
        report_types,
        [
            {
                "source_id": source_id,
                "external_id": ext_id,
                "code": code,
                "name": name,
                "ticker_indexed": ticker_indexed,
                "extraction_schema": schema,
                "enabled": True,
            }
            for ext_id, code, name, ticker_indexed, schema in VIETSTOCK_TYPES
        ],
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM report_types WHERE source_id = "
        "(SELECT id FROM sources WHERE code = 'vietstock')"
    )
    op.execute("DELETE FROM sources WHERE code = 'vietstock'")
