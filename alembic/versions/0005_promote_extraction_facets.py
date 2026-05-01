"""promote extraction facets to typed columns on report_extractions

Revision ID: 0005_promote_extraction_facets
Revises: 0004_conversations
Create Date: 2026-05-01

Adds five typed columns to `report_extractions` so the agent can filter the
catalogue on LLM-extracted classifications without parsing JSONB at query time:

  industry_name, topic, outlook, period, mentioned_tickers

Backfills from the existing `extras` JSONB so reports already extracted under
prior schema versions get their facets populated without re-running Gemini.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_promote_extraction_facets"
down_revision: str | None = "0004_conversations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "report_extractions",
        sa.Column("industry_name", sa.String(128), nullable=True),
    )
    op.add_column(
        "report_extractions",
        sa.Column("topic", sa.String(256), nullable=True),
    )
    op.add_column(
        "report_extractions",
        sa.Column("outlook", sa.String(16), nullable=True),
    )
    op.add_column(
        "report_extractions",
        sa.Column("period", sa.String(64), nullable=True),
    )
    op.add_column(
        "report_extractions",
        sa.Column(
            "mentioned_tickers",
            postgresql.ARRAY(sa.String(16)),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_extractions_outlook",
        "report_extractions",
        "outlook IS NULL OR outlook IN ('POSITIVE','NEUTRAL','NEGATIVE')",
    )
    op.create_index(
        "ix_report_extractions_industry_name",
        "report_extractions",
        ["industry_name"],
    )
    op.create_index(
        "ix_report_extractions_topic",
        "report_extractions",
        ["topic"],
    )
    op.create_index(
        "ix_report_extractions_outlook",
        "report_extractions",
        ["outlook"],
    )
    op.create_index(
        "ix_report_extractions_mentioned_tickers",
        "report_extractions",
        ["mentioned_tickers"],
        postgresql_using="gin",
    )

    # Backfill from existing extras JSONB. The schemas store these keys directly
    # in `extras` because the previous extractor stripped only `_HOT_FIELDS`.
    # Industry: extras->>'industry' and extras->>'outlook'
    op.execute(
        """
        UPDATE report_extractions
        SET industry_name = extras->>'industry'
        WHERE extras ? 'industry'
        """
    )
    op.execute(
        """
        UPDATE report_extractions
        SET outlook = extras->>'outlook'
        WHERE extras ? 'outlook'
          AND extras->>'outlook' IN ('POSITIVE','NEUTRAL','NEGATIVE')
        """
    )
    # Macro: market_outlook lives under that name in extras.
    op.execute(
        """
        UPDATE report_extractions
        SET outlook = extras->>'market_outlook'
        WHERE outlook IS NULL
          AND extras ? 'market_outlook'
          AND extras->>'market_outlook' IN ('POSITIVE','NEUTRAL','NEGATIVE')
        """
    )
    # Period: macro and technical schemas.
    op.execute(
        """
        UPDATE report_extractions
        SET period = extras->>'period'
        WHERE extras ? 'period'
        """
    )
    # Thematic: topic.
    op.execute(
        """
        UPDATE report_extractions
        SET topic = extras->>'topic'
        WHERE extras ? 'topic'
        """
    )
    # mentioned_tickers — union from each schema's ticker-bearing arrays.
    # industry.top_picks[].ticker
    op.execute(
        """
        UPDATE report_extractions
        SET mentioned_tickers = ARRAY(
            SELECT DISTINCT upper(trim(elem->>'ticker'))
            FROM jsonb_array_elements(extras->'top_picks') AS elem
            WHERE elem ? 'ticker' AND length(trim(elem->>'ticker')) > 0
        )
        WHERE extras ? 'top_picks'
          AND jsonb_typeof(extras->'top_picks') = 'array'
        """
    )
    # thematic.affected_tickers[].ticker
    op.execute(
        """
        UPDATE report_extractions
        SET mentioned_tickers = ARRAY(
            SELECT DISTINCT upper(trim(elem->>'ticker'))
            FROM jsonb_array_elements(extras->'affected_tickers') AS elem
            WHERE elem ? 'ticker' AND length(trim(elem->>'ticker')) > 0
        )
        WHERE extras ? 'affected_tickers'
          AND jsonb_typeof(extras->'affected_tickers') = 'array'
          AND mentioned_tickers IS NULL
        """
    )
    # technical.top_signals[].ticker + index_outlook[].symbol — combined.
    op.execute(
        """
        UPDATE report_extractions
        SET mentioned_tickers = ARRAY(
            SELECT DISTINCT v FROM (
                SELECT upper(trim(elem->>'ticker')) AS v
                FROM jsonb_array_elements(extras->'top_signals') AS elem
                WHERE elem ? 'ticker' AND length(trim(elem->>'ticker')) > 0
                UNION
                SELECT upper(trim(elem->>'symbol')) AS v
                FROM jsonb_array_elements(extras->'index_outlook') AS elem
                WHERE elem ? 'symbol' AND length(trim(elem->>'symbol')) > 0
            ) AS s
        )
        WHERE (extras ? 'top_signals' OR extras ? 'index_outlook')
          AND mentioned_tickers IS NULL
        """
    )
    # company: union the report's own ticker into mentioned_tickers.
    op.execute(
        """
        UPDATE report_extractions re
        SET mentioned_tickers = ARRAY[upper(r.ticker)]
        FROM reports r
        WHERE re.report_id = r.id
          AND r.ticker IS NOT NULL
          AND length(trim(r.ticker)) > 0
          AND re.mentioned_tickers IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_extractions_mentioned_tickers", table_name="report_extractions"
    )
    op.drop_index("ix_report_extractions_outlook", table_name="report_extractions")
    op.drop_index("ix_report_extractions_topic", table_name="report_extractions")
    op.drop_index(
        "ix_report_extractions_industry_name", table_name="report_extractions"
    )
    op.drop_constraint(
        "ck_extractions_outlook", "report_extractions", type_="check"
    )
    op.drop_column("report_extractions", "mentioned_tickers")
    op.drop_column("report_extractions", "period")
    op.drop_column("report_extractions", "outlook")
    op.drop_column("report_extractions", "topic")
    op.drop_column("report_extractions", "industry_name")
