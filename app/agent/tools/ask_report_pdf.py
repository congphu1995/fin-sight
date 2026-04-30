from uuid import UUID

from pydantic import BaseModel, Field

from app.agent.tools.base import Tool, ToolContext, register
from app.core.exceptions import LLMError, StorageError
from app.reports.models import Report


class AskReportPdfArgs(BaseModel):
    report_id: UUID = Field(..., description="UUID returned by search_reports")
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description=(
            "What you want to know from this PDF. Be specific — Gemini reads the "
            "PDF and answers only this query. Examples: 'What is the target price "
            "and the analyst's reasoning?', 'Summarize the risk section.'"
        ),
    )


@register
class AskReportPdf(Tool):
    name = "ask_report_pdf"
    description = (
        "Ask a focused question against a report's PDF. Gemini reads the full "
        "document and answers your `query`. Use this only when "
        "`get_report_metrics` doesn't have what you need — PDF reads are "
        "expensive. Returns a free-text answer."
    )
    args_schema = AskReportPdfArgs

    async def run(self, args: AskReportPdfArgs, ctx: ToolContext) -> dict:
        report = await ctx.session.get(Report, args.report_id)
        if report is None:
            return {"error": f"report {args.report_id} not found"}
        if not report.pdf_object_key:
            return {"error": f"report {args.report_id} has no stored PDF"}

        try:
            pdf_bytes = await ctx.minio.get_object(report.pdf_object_key)
        except StorageError as exc:
            return {"error": f"could not read PDF from storage: {exc}"}

        try:
            answer = await ctx.gemini.ask_about_pdf(pdf_bytes, args.query)
        except LLMError as exc:
            return {"error": f"Gemini PDF Q&A failed: {exc}"}

        return {
            "report_id": str(report.id),
            "ticker": report.ticker,
            "title": report.title,
            "query": args.query,
            "answer": answer,
        }
