"""Vocabulary discovery: list distinct values for an extraction facet.

Lets the agent see what values actually exist in the catalogue (e.g. is the
sector called "Steel" or "Thép"?) before guessing a filter for `search_reports`.
"""

from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.agent.tools.base import Tool, ToolContext, register
from app.reports.models import Report, ReportExtraction

Facet = Literal[
    "industry_name",
    "topic",
    "outlook",
    "recommendation",
    "publisher",
    "period",
]


class ListFacetsArgs(BaseModel):
    facet: Facet = Field(
        ...,
        description=(
            "Which extracted facet to enumerate. industry_name/topic/outlook/"
            "recommendation/period come from report_extractions; publisher comes "
            "from the report itself."
        ),
    )
    limit: int = Field(default=50, ge=1, le=200)


@register
class ListFacets(Tool):
    name = "list_facets"
    description = (
        "List the distinct values of an extraction facet (industry_name, topic, "
        "outlook, recommendation, period, publisher) ordered by frequency, with "
        "counts. Use BEFORE search_reports when unsure of the exact value the "
        "user means — e.g. confirm the catalogue calls it 'Steel' before "
        "filtering on it."
    )
    args_schema = ListFacetsArgs

    async def run(self, args: ListFacetsArgs, ctx: ToolContext) -> dict:
        if args.facet == "publisher":
            col = Report.publisher
            stmt = (
                select(col, func.count().label("count"))
                .where(col.is_not(None))
                .group_by(col)
                .order_by(func.count().desc(), col.asc())
                .limit(args.limit)
            )
        else:
            col = getattr(ReportExtraction, args.facet)
            stmt = (
                select(col, func.count().label("count"))
                .where(col.is_not(None))
                .group_by(col)
                .order_by(func.count().desc(), col.asc())
                .limit(args.limit)
            )

        rows = (await ctx.session.execute(stmt)).all()
        return {
            "facet": args.facet,
            "count": len(rows),
            "values": [{"value": r[0], "count": int(r[1])} for r in rows],
        }
