from datetime import date

from pydantic import BaseModel, Field
from sqlalchemy import exists, select

from app.agent.tools.base import Tool, ToolContext, register
from app.reports.models import Report, ReportExtraction, ReportType, Source


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
    limit: int = Field(default=20, ge=1, le=50)


@register
class SearchReports(Tool):
    name = "search_reports"
    description = (
        "Search the internal reports catalogue. Filter by ticker, report type, "
        "and a published-date range. Returns up to `limit` rows, newest first. "
        "Use this before `get_report_metrics` to find a report_id."
    )
    args_schema = SearchReportsArgs

    async def run(self, args: SearchReportsArgs, ctx: ToolContext) -> dict:
        has_extraction = exists().where(ReportExtraction.report_id == Report.id)
        stmt = (
            select(
                Report.id,
                Report.ticker,
                Report.title,
                Report.published_at,
                Report.publisher,
                ReportType.code.label("report_type_code"),
                Source.code.label("source_code"),
                has_extraction.label("has_extraction"),
            )
            .join(ReportType, Report.report_type_id == ReportType.id)
            .join(Source, Report.source_id == Source.id)
            .order_by(Report.published_at.desc().nulls_last(), Report.discovered_at.desc())
            .limit(args.limit)
        )
        if args.ticker:
            stmt = stmt.where(Report.ticker == args.ticker.upper())
        if args.report_type_code:
            stmt = stmt.where(ReportType.code == args.report_type_code)
        if args.since:
            stmt = stmt.where(Report.published_at >= args.since)
        if args.until:
            stmt = stmt.where(Report.published_at <= args.until)

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
