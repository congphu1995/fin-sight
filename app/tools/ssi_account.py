"""SSI FastConnect Trading tools (Tier 2, YOUR account, READ-ONLY).

These expose your own positions/balances/orders. They are non-mutating; the
underlying client implements no order-placement path (see app/core/ssi).
"""

from datetime import date

from pydantic import BaseModel, Field

from app.core.exceptions import SsiError
from app.tools.base import Tool, ToolContext, register
from app.tools.ssi_common import NOT_CONFIGURED_TRADING, envelope, fmt_date


class NoArgs(BaseModel):
    pass


@register
class SsiMyPositions(Tool):
    name = "ssi_my_positions"
    description = (
        "Your current SSI stock holdings — symbol, quantity, average cost and "
        "market value. Read-only; your own account."
    )
    args_schema = NoArgs

    async def run(self, args: NoArgs, ctx: ToolContext) -> dict:
        if ctx.ssi_trading is None:
            return dict(NOT_CONFIGURED_TRADING)
        try:
            resp = await ctx.ssi_trading.stock_position()
        except SsiError as exc:
            return {"error": str(exc)}
        return {"account": ctx.ssi_trading.account_id, **envelope(resp)}


@register
class SsiMyCashBalance(Tool):
    name = "ssi_my_cash_balance"
    description = "Your SSI cash account balance and buying power. Read-only; your own account."
    args_schema = NoArgs

    async def run(self, args: NoArgs, ctx: ToolContext) -> dict:
        if ctx.ssi_trading is None:
            return dict(NOT_CONFIGURED_TRADING)
        try:
            resp = await ctx.ssi_trading.cash_balance()
        except SsiError as exc:
            return {"error": str(exc)}
        return {"account": ctx.ssi_trading.account_id, **envelope(resp)}


class SsiMyOrdersArgs(BaseModel):
    from_date: date | None = Field(
        default=None,
        description="With to_date: order HISTORY for the range; omit both for the order book.",
    )
    to_date: date | None = Field(default=None, description="End date for order history.")


@register
class SsiMyOrders(Tool):
    name = "ssi_my_orders"
    description = (
        "Your SSI orders — today's order book by default, or order history when a "
        "from_date/to_date range is given. Read-only; your own account."
    )
    args_schema = SsiMyOrdersArgs

    async def run(self, args: SsiMyOrdersArgs, ctx: ToolContext) -> dict:
        if ctx.ssi_trading is None:
            return dict(NOT_CONFIGURED_TRADING)
        try:
            if args.from_date and args.to_date:
                resp = await ctx.ssi_trading.order_history(
                    fmt_date(args.from_date), fmt_date(args.to_date)
                )
            else:
                resp = await ctx.ssi_trading.order_book()
        except SsiError as exc:
            return {"error": str(exc)}
        return {"account": ctx.ssi_trading.account_id, **envelope(resp)}


@register
class SsiMyDerivPositions(Tool):
    name = "ssi_my_deriv_positions"
    description = (
        "Your SSI derivatives (futures) positions and derivative account balance. "
        "Read-only; your own account."
    )
    args_schema = NoArgs

    async def run(self, args: NoArgs, ctx: ToolContext) -> dict:
        if ctx.ssi_trading is None:
            return dict(NOT_CONFIGURED_TRADING)
        try:
            positions = await ctx.ssi_trading.derivative_position()
            balance = await ctx.ssi_trading.derivative_balance()
        except SsiError as exc:
            return {"error": str(exc)}
        return {
            "account": ctx.ssi_trading.account_id,
            "positions": envelope(positions),
            "balance": envelope(balance),
        }
