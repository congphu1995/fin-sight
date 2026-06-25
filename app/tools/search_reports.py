from datetime import date
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import exists, literal, select

from app.reports.models import Report, ReportExtraction, ReportType, Source
from app.tools.base import Tool, ToolContext, register

_BASE_DESCRIPTION = (
    "Search the internal reports catalogue. Filter by ticker, report type, "
    "published-date range, and LLM-extracted facets (industry_name, topic, "
    "outlook, recommendation, mentions_ticker, has_extraction). Returns up "
    "to `limit` rows, newest first. Use this before `get_report_metrics` to "
    "find a report_id."
)

# Per-facet field descriptions. (Use list_facets to discover the catalogue's
# actual vocabulary before filtering on free-text facets.)
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
            "Report type slug: 'company', 'industry', 'macro', 'technical', 'thematic', 'generic'"
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
        needs_extraction_join = (
            any(
                v is not None
                for v in (
                    args.industry_name,
                    args.topic,
                    args.outlook,
                    args.recommendation,
                    args.mentions_ticker,
                )
            )
            or args.has_extraction is True
        )

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
                select(ReportExtraction.id).where(ReportExtraction.report_id == Report.id).exists()
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
