from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agent.tools.base import Tool, ToolContext, register
from app.reports.models import ReportExtraction


class GetReportMetricsArgs(BaseModel):
    report_id: UUID = Field(..., description="UUID returned by search_reports")


@register
class GetReportMetrics(Tool):
    name = "get_report_metrics"
    description = (
        "Return the LLM-extracted metrics for a single report: summary, "
        "recommendation, target price, horizon, and free-form extras. "
        "Use a `report_id` from `search_reports`."
    )
    args_schema = GetReportMetricsArgs

    async def run(self, args: GetReportMetricsArgs, ctx: ToolContext) -> dict:
        stmt = (
            select(ReportExtraction)
            .where(ReportExtraction.report_id == args.report_id)
            .order_by(ReportExtraction.extracted_at.desc())
            .limit(1)
        )
        row = (await ctx.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return {"error": f"no extraction found for report_id={args.report_id}"}
        return {
            "report_id": str(row.report_id),
            "model": row.model,
            "prompt_version": row.prompt_version,
            "extracted_at": row.extracted_at.isoformat(),
            "summary": row.summary,
            "recommendation": row.recommendation,
            "target_price": float(row.target_price) if row.target_price is not None else None,
            "target_currency": row.target_currency,
            "horizon": row.horizon,
            "extras": row.extras,
        }
