"""Tool catalog — importing this package registers every tool via @register.

Order matches a rough usage flow: search → fetch metrics → external lookups.
Agents pick from this catalog via `AgentSpec.tool_names`.
"""

from app.agent.tools.ask_report_pdf import AskReportPdf
from app.agent.tools.base import TOOL_REGISTRY, Tool, ToolContext, register
from app.agent.tools.fetch_url import FetchUrl
from app.agent.tools.get_report_metrics import GetReportMetrics
from app.agent.tools.search_reports import SearchReports
from app.agent.tools.web_search import WebSearch

__all__ = [
    "TOOL_REGISTRY",
    "Tool",
    "ToolContext",
    "register",
    "SearchReports",
    "GetReportMetrics",
    "WebSearch",
    "FetchUrl",
    "AskReportPdf",
]
