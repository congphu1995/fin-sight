"""The MCP server lists the right tools, all read-only, via an in-memory client."""

from mcp.shared.memory import create_connected_server_and_client_session as connect

from app.core.config import Settings
from app.mcp.server import build_mcp_server

REPORT_TOOLS = {
    "get_stock_analysis",
    "search_reports",
    "get_report_metrics",
    "list_facets",
    "ask_report_pdf",
}
SSI_TOOLS = {
    "ssi_daily_ohlc",
    "ssi_securities",
    "ssi_index_components",
    "ssi_daily_price",
    "ssi_my_positions",
    "ssi_my_cash_balance",
    "ssi_my_orders",
    "ssi_my_deriv_positions",
}


def _disabled_settings() -> Settings:
    # Force SSI off regardless of any ambient env / .env.
    return Settings(
        ssi_data_consumer_id="",
        ssi_data_consumer_secret="",
        ssi_trading_consumer_id="",
        ssi_trading_consumer_secret="",
        ssi_trading_pin="",
        ssi_trading_account_id="",
    )


def _enabled_settings() -> Settings:
    return Settings(
        ssi_data_consumer_id="x",
        ssi_data_consumer_secret="y",
        ssi_trading_consumer_id="a",
        ssi_trading_consumer_secret="b",
        ssi_trading_pin="1234",
        ssi_trading_account_id="ACC1",
    )


async def test_lists_report_tools_all_read_only() -> None:
    mcp = build_mcp_server(_disabled_settings())
    async with connect(mcp._mcp_server) as client:
        tools = (await client.list_tools()).tools
        names = {t.name for t in tools}
        assert names >= REPORT_TOOLS
        assert not any(n.startswith("ssi_") for n in names)  # SSI disabled
        for t in tools:
            assert t.annotations is not None and t.annotations.readOnlyHint is True


async def test_lists_ssi_tools_when_enabled() -> None:
    mcp = build_mcp_server(_enabled_settings())
    async with connect(mcp._mcp_server) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        assert names >= SSI_TOOLS
        assert names >= REPORT_TOOLS
