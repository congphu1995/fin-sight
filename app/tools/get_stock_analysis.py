from pydantic import BaseModel, Field
from sqlalchemy import select

from app.reports.models import Report, ReportExtraction, ReportType
from app.tools.base import Tool, ToolContext, register


class GetStockAnalysisArgs(BaseModel):
    ticker: str = Field(..., description="Stock ticker, e.g. 'HPG'")
    limit: int = Field(
        default=5, ge=1, le=20, description="How many recent extracted reports to include"
    )


@register
class GetStockAnalysis(Tool):
    name = "get_stock_analysis"
    description = (
        "Digested analyst view for one ticker: the most recent LLM-extracted "
        "reports on it (recommendation, target price, outlook, summary), newest "
        "first. Start here for a stock, then drill into a specific report with "
        "get_report_metrics or ask_report_pdf. Returns count=0 when none exist — "
        "fall back to search_reports(mentions_ticker=...) for reports that only "
        "mention the ticker."
    )
    args_schema = GetStockAnalysisArgs

    async def run(self, args: GetStockAnalysisArgs, ctx: ToolContext) -> dict:
        ticker = args.ticker.upper()
        stmt = (
            select(
                Report.id,
                Report.title,
                Report.published_at,
                Report.publisher,
                ReportType.code.label("report_type_code"),
                ReportExtraction.summary,
                ReportExtraction.recommendation,
                ReportExtraction.target_price,
                ReportExtraction.target_currency,
                ReportExtraction.outlook,
                ReportExtraction.horizon,
            )
            .join(ReportType, Report.report_type_id == ReportType.id)
            .join(ReportExtraction, ReportExtraction.report_id == Report.id)
            .where(Report.ticker == ticker)
            .order_by(
                Report.published_at.desc().nulls_last(),
                ReportExtraction.extracted_at.desc(),
            )
            .limit(args.limit)
        )
        rows = (await ctx.session.execute(stmt)).all()
        reports = [
            {
                "report_id": str(r.id),
                "title": r.title,
                "published_at": r.published_at.isoformat() if r.published_at else None,
                "publisher": r.publisher,
                "report_type_code": r.report_type_code,
                "recommendation": r.recommendation,
                "target_price": float(r.target_price) if r.target_price is not None else None,
                "target_currency": r.target_currency,
                "outlook": r.outlook,
                "horizon": r.horizon,
                "summary": r.summary,
            }
            for r in rows
        ]
        return {"ticker": ticker, "count": len(reports), "reports": reports}
