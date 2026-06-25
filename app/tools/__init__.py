"""Tool catalog — importing this package registers every tool via @register.

These read-only tools are the query layer the MCP server exposes to the agent.
The Tool/registry abstraction is kept (each tool carries a name + Pydantic args
schema + run()), so the MCP wrappers and tests can reuse them unchanged.

Tier 1 (stored, cheap): get_stock_analysis · search_reports · get_report_metrics ·
list_facets · ask_report_pdf (drill-down). Tier 2 (live SSI): ssi_* tools.
"""

from app.tools.ask_report_pdf import AskReportPdf
from app.tools.base import TOOL_REGISTRY, Tool, ToolContext, register
from app.tools.get_report_metrics import GetReportMetrics
from app.tools.get_stock_analysis import GetStockAnalysis
from app.tools.list_facets import ListFacets
from app.tools.search_reports import SearchReports
from app.tools.ssi_account import (
    SsiMyCashBalance,
    SsiMyDerivPositions,
    SsiMyOrders,
    SsiMyPositions,
)
from app.tools.ssi_market import (
    SsiDailyOhlc,
    SsiDailyStockPrice,
    SsiIndexComponents,
    SsiSecurities,
)

__all__ = [
    "TOOL_REGISTRY",
    "Tool",
    "ToolContext",
    "register",
    "SearchReports",
    "GetReportMetrics",
    "GetStockAnalysis",
    "ListFacets",
    "AskReportPdf",
    "SsiDailyOhlc",
    "SsiSecurities",
    "SsiIndexComponents",
    "SsiDailyStockPrice",
    "SsiMyPositions",
    "SsiMyCashBalance",
    "SsiMyOrders",
    "SsiMyDerivPositions",
]
