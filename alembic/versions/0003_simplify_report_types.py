"""simplify report_types: drop external_id and extraction_schema, repurpose code as universal slug

Revision ID: 0003_simplify_report_types
Revises: 0002_seed_vietstock
Create Date: 2026-04-28

The old layout had three source-flavored ID-ish columns:
- external_id   = Vietstock's '58'
- code          = URL slug 'phan-tich-doanh-nghiep'
- extraction_schema = our universal slug 'company'

`code` is now repurposed to be the universal slug ('company', 'industry', ...)
that the public surface (CLI, API, logs) speaks. The mapping to a source's API
filter value (Vietstock's '58') moves into the crawler class.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_simplify_report_types"
down_revision: str | None = "0002_seed_vietstock"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Promote extraction_schema → code (overwrites the URL-slug values).
    op.execute("UPDATE report_types SET code = extraction_schema")

    op.drop_constraint("uq_report_types_source_external", "report_types", type_="unique")
    op.drop_column("report_types", "external_id")
    op.drop_column("report_types", "extraction_schema")
    op.create_unique_constraint(
        "uq_report_types_source_code", "report_types", ["source_id", "code"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_report_types_source_code", "report_types", type_="unique")
    op.add_column(
        "report_types",
        sa.Column("extraction_schema", sa.String(64), nullable=True),
    )
    op.add_column(
        "report_types",
        sa.Column("external_id", sa.String(64), nullable=True),
    )
    # Best-effort restore: copy code back into extraction_schema; external_id is lost.
    op.execute("UPDATE report_types SET extraction_schema = code")
    op.execute("UPDATE report_types SET external_id = code")
    op.alter_column("report_types", "extraction_schema", nullable=False)
    op.alter_column("report_types", "external_id", nullable=False)
    op.create_unique_constraint(
        "uq_report_types_source_external", "report_types", ["source_id", "external_id"]
    )
