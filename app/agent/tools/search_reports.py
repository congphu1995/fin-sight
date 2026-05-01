from datetime import date
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import exists, func, literal, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agent.tools.base import Tool, ToolContext, register
from app.reports.models import Report, ReportExtraction, ReportType, Source

_BASE_DESCRIPTION = (
    "Search the internal reports catalogue. Filter by ticker, report type, "
    "published-date range, and LLM-extracted facets (industry_name, topic, "
    "outlook, recommendation, mentions_ticker, has_extraction). Returns up "
    "to `limit` rows, newest first. Use this before `get_report_metrics` to "
    "find a report_id."
)

# Base descriptions for facets that get top-N values appended at startup by
# `refresh_facet_hints`. Stored as constants so we can recompose without
# accumulating stale value lists across reloads.
_BASE_FIELD_DESC: dict[str, str] = {
    "industry_name": (
        "Sector for report_type_code='industry' ONLY (e.g. 'Steel', 'Banks', "
        "'Real Estate'). Do NOT use this with thematic reports — use `topic` "
        "for those. Free-text ILIKE."
    ),
    "topic": (
        "Theme for report_type_code='thematic' ONLY (e.g. 'EV transition', "
        "'VN-US trade'). Do NOT use this for industry sectors — use "
        "`industry_name` for those. Free-text ILIKE."
    ),
}


class SearchReportsArgs(BaseModel):
    ticker: str | None = Field(default=None, description="Stock ticker, e.g. 'HPG'")
    report_type_code: str | None = Field(
        default=None,
        description=(
            "Report type slug: 'company', 'industry', 'macro', 'technical', "
            "'thematic', 'generic'"
        ),
    )
    since: date | None = Field(default=None, description="Earliest published_at (inclusive)")
    until: date | None = Field(default=None, description="Latest published_at (inclusive)")
    industry_name: str | None = Field(
        default=None,
        description=_BASE_FIELD_DESC["industry_name"],
    )
    topic: str | None = Field(
        default=None,
        description=_BASE_FIELD_DESC["topic"],
    )
    outlook: Literal["POSITIVE", "NEUTRAL", "NEGATIVE"] | None = Field(
        default=None,
        description="Whole-report sentiment for industry/macro reports.",
    )
    recommendation: str | None = Field(
        default=None,
        description=(
            "Analyst recommendation on company reports: BUY, HOLD, SELL, "
            "ACCUMULATE, REDUCE, OUTPERFORM, UNDERPERFORM, NEUTRAL."
        ),
    )
    mentions_ticker: str | None = Field(
        default=None,
        description=(
            "Ticker that appears anywhere the report touches — top picks, "
            "affected tickers, technical signals, or the report's own ticker. "
            "Wider than `ticker` (which only matches the report's primary symbol)."
        ),
    )
    has_extraction: bool | None = Field(
        default=None,
        description="If True, only return reports that have been LLM-extracted.",
    )
    limit: int = Field(default=20, ge=1, le=50)


@register
class SearchReports(Tool):
    name = "search_reports"
    description = _BASE_DESCRIPTION
    args_schema = SearchReportsArgs

    async def run(self, args: SearchReportsArgs, ctx: ToolContext) -> dict:
        # Decide whether we need to JOIN report_extractions.
        needs_extraction_join = any(
            v is not None
            for v in (
                args.industry_name,
                args.topic,
                args.outlook,
                args.recommendation,
                args.mentions_ticker,
            )
        ) or args.has_extraction is True

        # When we INNER JOIN report_extractions, has_extraction is trivially true;
        # otherwise compute it via a correlated EXISTS subquery for the SELECT.
        if needs_extraction_join:
            has_extraction_col = literal(True).label("has_extraction")
        else:
            has_extraction_col = (
                exists().where(ReportExtraction.report_id == Report.id).label("has_extraction")
            )

        stmt = (
            select(
                Report.id,
                Report.ticker,
                Report.title,
                Report.published_at,
                Report.publisher,
                ReportType.code.label("report_type_code"),
                Source.code.label("source_code"),
                has_extraction_col,
            )
            .join(ReportType, Report.report_type_id == ReportType.id)
            .join(Source, Report.source_id == Source.id)
            .order_by(Report.published_at.desc().nulls_last(), Report.discovered_at.desc())
            .limit(args.limit)
        )
        if needs_extraction_join:
            # INNER JOIN — every extraction-derived filter implies the report
            # must have an extraction row. has_extraction=True also lands here.
            stmt = stmt.join(ReportExtraction, ReportExtraction.report_id == Report.id)
        elif args.has_extraction is False:
            not_extracted = ~(
                select(ReportExtraction.id)
                .where(ReportExtraction.report_id == Report.id)
                .exists()
            )
            stmt = stmt.where(not_extracted)

        if args.ticker:
            stmt = stmt.where(Report.ticker == args.ticker.upper())
        if args.report_type_code:
            stmt = stmt.where(ReportType.code == args.report_type_code)
        if args.since:
            stmt = stmt.where(Report.published_at >= args.since)
        if args.until:
            stmt = stmt.where(Report.published_at <= args.until)
        if args.industry_name:
            stmt = stmt.where(ReportExtraction.industry_name.ilike(f"%{args.industry_name}%"))
        if args.topic:
            stmt = stmt.where(ReportExtraction.topic.ilike(f"%{args.topic}%"))
        if args.outlook:
            stmt = stmt.where(ReportExtraction.outlook == args.outlook)
        if args.recommendation:
            stmt = stmt.where(ReportExtraction.recommendation == args.recommendation.upper())
        if args.mentions_ticker:
            stmt = stmt.where(
                ReportExtraction.mentioned_tickers.contains([args.mentions_ticker.upper()])
            )

        rows = (await ctx.session.execute(stmt)).all()
        return {
            "count": len(rows),
            "reports": [
                {
                    "report_id": str(r.id),
                    "ticker": r.ticker,
                    "title": r.title,
                    "published_at": r.published_at.isoformat() if r.published_at else None,
                    "publisher": r.publisher,
                    "report_type_code": r.report_type_code,
                    "source_code": r.source_code,
                    "has_extraction": bool(r.has_extraction),
                }
                for r in rows
            ],
        }


async def refresh_facet_hints(
    session_factory: async_sessionmaker, top_n: int = 30
) -> dict[str, int]:
    """Bake the catalogue's actual vocabulary into per-field descriptions on
    `SearchReportsArgs` so Gemini's tool-use planner sees concrete values when
    routing free-text filters (e.g. it picks `industry_name='Steel'` instead of
    `topic='thép'` because only `industry_name` carries known values).

    Mutates `SearchReportsArgs.model_fields[name].description` and rebuilds the
    Pydantic core schema so the next `model_json_schema()` call reflects it.
    The agent loop reads `args_schema.model_json_schema()` per turn, so the
    rebuild is picked up without restarting.

    Called from app.main lifespan once per process. Failures are logged by the
    caller and never fatal — fields fall back to their base descriptions.
    """
    facet_columns = {
        "industry_name": ReportExtraction.industry_name,
        "topic": ReportExtraction.topic,
    }
    counts: dict[str, int] = {}
    async with session_factory() as session:
        for name, col in facet_columns.items():
            stmt = (
                select(col, func.count().label("c"))
                .where(col.is_not(None))
                .group_by(col)
                .order_by(func.count().desc())
                .limit(top_n)
            )
            rows = (await session.execute(stmt)).all()
            values = [r[0] for r in rows if r[0]]
            base = _BASE_FIELD_DESC[name]
            if values:
                desc = (
                    f"{base} Known values in the catalogue (most frequent first): "
                    + ", ".join(values)
                    + ". If none match, call list_facets first."
                )
            else:
                desc = base
            SearchReportsArgs.model_fields[name].description = desc
            counts[name] = len(values)

    SearchReportsArgs.model_rebuild(force=True)
    return counts
