"""FastMCP server: wraps the read-only tool registry as MCP tools.

Each wrapper takes the underlying tool's Pydantic args model as its single
parameter, so the MCP input schema is the tool's `args_schema` (one source of
truth). Every tool is annotated readOnlyHint=True (Mira auto-runs them, no
approval card). SSI tools register only when their integration is configured.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from app.core.config import Settings
from app.dependencies import (
    get_gemini,
    get_logger,
    get_minio_client,
    get_session_factory,
    get_ssi_data_client,
    get_ssi_trading_client,
)
from app.mcp.render import (
    render_ask_pdf,
    render_facets,
    render_report_metrics,
    render_search_reports,
    render_ssi_account,
    render_ssi_market,
    render_stock_analysis,
)
from app.tools import TOOL_REGISTRY, ToolContext
from app.tools.ask_report_pdf import AskReportPdfArgs
from app.tools.get_report_metrics import GetReportMetricsArgs
from app.tools.get_stock_analysis import GetStockAnalysisArgs
from app.tools.list_facets import ListFacetsArgs
from app.tools.search_reports import SearchReportsArgs
from app.tools.ssi_account import NoArgs, SsiMyOrdersArgs
from app.tools.ssi_market import (
    SsiDailyOhlcArgs,
    SsiDailyStockPriceArgs,
    SsiIndexComponentsArgs,
    SsiSecuritiesArgs,
)

READ_ONLY = ToolAnnotations(readOnlyHint=True)

_INSTRUCTIONS = (
    "FinSight exposes Vietnamese-equity research (crawled analyst reports, "
    "pre-digested per stock) plus live SSI market data and your own SSI account "
    "(read-only). Start with get_stock_analysis for a ticker's digested view; "
    "use search_reports/list_facets to explore, get_report_metrics/ask_report_pdf "
    "to drill in, and the ssi_* tools for live prices and your holdings."
)


async def _run(tool_name: str, args, render) -> str:
    """Build a per-call ToolContext from the singletons, run the tool, render text."""
    factory = get_session_factory()
    async with factory() as session:
        ctx = ToolContext(
            session=session,
            minio=get_minio_client(),
            gemini=get_gemini(),
            logger=get_logger(),
            ssi_data=get_ssi_data_client(),
            ssi_trading=get_ssi_trading_client(),
        )
        result = await TOOL_REGISTRY[tool_name].run(args, ctx)
    return render(result)


def build_mcp_server(settings: Settings) -> FastMCP:
    mcp = FastMCP(name="finsight", instructions=_INSTRUCTIONS, streamable_http_path="/")

    # --- Tier 1: stored reports (always available) ---
    @mcp.tool(name="get_stock_analysis", annotations=READ_ONLY)
    async def get_stock_analysis(args: GetStockAnalysisArgs) -> str:
        return await _run("get_stock_analysis", args, render_stock_analysis)

    @mcp.tool(name="search_reports", annotations=READ_ONLY)
    async def search_reports(args: SearchReportsArgs) -> str:
        return await _run("search_reports", args, render_search_reports)

    @mcp.tool(name="get_report_metrics", annotations=READ_ONLY)
    async def get_report_metrics(args: GetReportMetricsArgs) -> str:
        return await _run("get_report_metrics", args, render_report_metrics)

    @mcp.tool(name="list_facets", annotations=READ_ONLY)
    async def list_facets(args: ListFacetsArgs) -> str:
        return await _run("list_facets", args, render_facets)

    @mcp.tool(name="ask_report_pdf", annotations=READ_ONLY)
    async def ask_report_pdf(args: AskReportPdfArgs) -> str:
        return await _run("ask_report_pdf", args, render_ask_pdf)

    # --- Tier 2a: live SSI market data ---
    if settings.ssi_data_enabled:

        @mcp.tool(name="ssi_daily_ohlc", annotations=READ_ONLY)
        async def ssi_daily_ohlc(args: SsiDailyOhlcArgs) -> str:
            return await _run("ssi_daily_ohlc", args, render_ssi_market)

        @mcp.tool(name="ssi_securities", annotations=READ_ONLY)
        async def ssi_securities(args: SsiSecuritiesArgs) -> str:
            return await _run("ssi_securities", args, render_ssi_market)

        @mcp.tool(name="ssi_index_components", annotations=READ_ONLY)
        async def ssi_index_components(args: SsiIndexComponentsArgs) -> str:
            return await _run("ssi_index_components", args, render_ssi_market)

        @mcp.tool(name="ssi_daily_price", annotations=READ_ONLY)
        async def ssi_daily_price(args: SsiDailyStockPriceArgs) -> str:
            return await _run("ssi_daily_price", args, render_ssi_market)

    # --- Tier 2b: live SSI personal account (READ-ONLY) ---
    if settings.ssi_trading_enabled:

        @mcp.tool(name="ssi_my_positions", annotations=READ_ONLY)
        async def ssi_my_positions() -> str:
            return await _run("ssi_my_positions", NoArgs(), render_ssi_account)

        @mcp.tool(name="ssi_my_cash_balance", annotations=READ_ONLY)
        async def ssi_my_cash_balance() -> str:
            return await _run("ssi_my_cash_balance", NoArgs(), render_ssi_account)

        @mcp.tool(name="ssi_my_orders", annotations=READ_ONLY)
        async def ssi_my_orders(args: SsiMyOrdersArgs) -> str:
            return await _run("ssi_my_orders", args, render_ssi_account)

        @mcp.tool(name="ssi_my_deriv_positions", annotations=READ_ONLY)
        async def ssi_my_deriv_positions() -> str:
            return await _run("ssi_my_deriv_positions", NoArgs(), render_ssi_account)

    return mcp
