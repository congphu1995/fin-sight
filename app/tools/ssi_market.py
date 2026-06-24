"""SSI FastConnect Data tools (Tier 2, live market data — non-personal)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.core.exceptions import SsiError
from app.tools.base import Tool, ToolContext, register
from app.tools.ssi_common import NOT_CONFIGURED_DATA, envelope, fmt_date

Market = Literal["HOSE", "HNX", "UPCOM", "DER"]


class SsiDailyOhlcArgs(BaseModel):
    symbol: str = Field(..., description="Ticker, e.g. 'VNM'")
    from_date: date = Field(..., description="Start trading date (inclusive)")
    to_date: date = Field(..., description="End trading date (inclusive)")


@register
class SsiDailyOhlc(Tool):
    name = "ssi_daily_ohlc"
    description = (
        "Live daily OHLCV bars for a ticker from SSI FastConnect Data — open, "
        "high, low, close and volume per trading day over the date range."
    )
    args_schema = SsiDailyOhlcArgs

    async def run(self, args: SsiDailyOhlcArgs, ctx: ToolContext) -> dict:
        if ctx.ssi_data is None:
            return dict(NOT_CONFIGURED_DATA)
        try:
            resp = await ctx.ssi_data.daily_ohlc(
                args.symbol.upper(),
                fmt_date(args.from_date),
                fmt_date(args.to_date),
                page_size=500,
            )
        except SsiError as exc:
            return {"error": str(exc)}
        return {"symbol": args.symbol.upper(), **envelope(resp)}


class SsiSecuritiesArgs(BaseModel):
    market: Market = Field(
        default="HOSE", description="Exchange: HOSE, HNX, UPCOM, or DER (derivatives)"
    )


@register
class SsiSecurities(Tool):
    name = "ssi_securities"
    description = (
        "List the securities (symbols) trading on an SSI exchange "
        "(HOSE/HNX/UPCOM/DER) from SSI FastConnect Data."
    )
    args_schema = SsiSecuritiesArgs

    async def run(self, args: SsiSecuritiesArgs, ctx: ToolContext) -> dict:
        if ctx.ssi_data is None:
            return dict(NOT_CONFIGURED_DATA)
        try:
            resp = await ctx.ssi_data.securities(args.market)
        except SsiError as exc:
            return {"error": str(exc)}
        return {"market": args.market, **envelope(resp)}


class SsiIndexComponentsArgs(BaseModel):
    index_code: str = Field(..., description="Index code, e.g. 'VN30', 'HNX30', 'VNINDEX'")


@register
class SsiIndexComponents(Tool):
    name = "ssi_index_components"
    description = (
        "List the constituent tickers of a market index (e.g. VN30) from SSI FastConnect Data."
    )
    args_schema = SsiIndexComponentsArgs

    async def run(self, args: SsiIndexComponentsArgs, ctx: ToolContext) -> dict:
        if ctx.ssi_data is None:
            return dict(NOT_CONFIGURED_DATA)
        try:
            resp = await ctx.ssi_data.index_components(args.index_code.upper())
        except SsiError as exc:
            return {"error": str(exc)}
        return {"index": args.index_code.upper(), **envelope(resp)}


class SsiDailyStockPriceArgs(BaseModel):
    symbol: str = Field(..., description="Ticker, e.g. 'VNM'")
    from_date: date = Field(..., description="Start trading date (inclusive)")
    to_date: date = Field(..., description="End trading date (inclusive)")


@register
class SsiDailyStockPrice(Tool):
    name = "ssi_daily_price"
    description = (
        "Live daily price detail for a ticker from SSI FastConnect Data — close, "
        "change, traded value, and foreign buy/sell room per trading day."
    )
    args_schema = SsiDailyStockPriceArgs

    async def run(self, args: SsiDailyStockPriceArgs, ctx: ToolContext) -> dict:
        if ctx.ssi_data is None:
            return dict(NOT_CONFIGURED_DATA)
        try:
            resp = await ctx.ssi_data.daily_stock_price(
                args.symbol.upper(),
                fmt_date(args.from_date),
                fmt_date(args.to_date),
                page_size=500,
            )
        except SsiError as exc:
            return {"error": str(exc)}
        return {"symbol": args.symbol.upper(), **envelope(resp)}
