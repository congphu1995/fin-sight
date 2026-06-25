"""SSI tools shape the SDK envelope and degrade when not configured."""

from datetime import date

import structlog

from app.tools.base import ToolContext
from app.tools.ssi_account import NoArgs, SsiMyOrders, SsiMyOrdersArgs, SsiMyPositions
from app.tools.ssi_market import SsiDailyOhlc, SsiDailyOhlcArgs, SsiSecurities, SsiSecuritiesArgs


class FakeSsiData:
    async def daily_ohlc(self, *a, **k) -> dict:
        return {
            "status": 200,
            "message": "Success",
            "data": [{"TradingDate": "02/01/2024", "Close": 78.5}],
        }

    async def securities(self, *a, **k) -> dict:
        return {"status": 200, "message": "Success", "data": [{"Symbol": "VNM"}]}


class FakeSsiTrading:
    account_id = "ACC1"

    async def stock_position(self) -> dict:
        return {"status": 200, "data": [{"symbol": "VNM", "quantity": 100}]}

    async def order_book(self) -> dict:
        return {"status": 200, "data": []}

    async def order_history(self, start: str, end: str) -> dict:
        return {"status": 200, "data": [{"orderID": "1"}]}


def _ctx(ssi_data=None, ssi_trading=None) -> ToolContext:
    return ToolContext(
        session=None,  # type: ignore[arg-type]
        minio=None,  # type: ignore[arg-type]
        gemini=None,  # type: ignore[arg-type]
        logger=structlog.get_logger(),
        ssi_data=ssi_data,
        ssi_trading=ssi_trading,
    )


async def test_daily_ohlc_uppercases_and_shapes_envelope() -> None:
    out = await SsiDailyOhlc().run(
        SsiDailyOhlcArgs(symbol="vnm", from_date=date(2024, 1, 1), to_date=date(2024, 1, 2)),
        _ctx(ssi_data=FakeSsiData()),
    )
    assert out["symbol"] == "VNM"
    assert out["status"] == 200
    assert isinstance(out["data"], list)


async def test_market_tool_not_configured() -> None:
    out = await SsiSecurities().run(SsiSecuritiesArgs(), _ctx())
    assert "error" in out


async def test_my_positions_includes_account() -> None:
    out = await SsiMyPositions().run(NoArgs(), _ctx(ssi_trading=FakeSsiTrading()))
    assert out["account"] == "ACC1"
    assert out["status"] == 200


async def test_my_orders_book_vs_history() -> None:
    t = FakeSsiTrading()
    book = await SsiMyOrders().run(SsiMyOrdersArgs(), _ctx(ssi_trading=t))
    assert book["data"] == []  # today's order book
    hist = await SsiMyOrders().run(
        SsiMyOrdersArgs(from_date=date(2024, 1, 1), to_date=date(2024, 1, 31)),
        _ctx(ssi_trading=t),
    )
    assert hist["data"] == [{"orderID": "1"}]  # history when range given
