"""SSI client facades: caching/error wrapping, and the read-only guarantee."""

import pytest

from app.core.exceptions import SsiError
from app.core.ssi.data_client import SsiDataClient
from app.core.ssi.trading_client import SsiTradingClient


async def test_data_client_caches_within_ttl() -> None:
    c = SsiDataClient(consumer_id="x", consumer_secret="y", url="http://t", cache_ttl_seconds=100)
    calls: list[str] = []

    def fake(method: str, build_req) -> dict:
        calls.append(method)
        return {"status": 200, "data": [{"close": 1}]}

    c._sync_call = fake  # type: ignore[method-assign]
    r1 = await c.daily_ohlc("VNM", "01/01/2024", "02/01/2024")
    r2 = await c.daily_ohlc("VNM", "01/01/2024", "02/01/2024")
    assert r1 == r2
    assert calls == ["daily_ohlc"]  # second served from cache


async def test_data_client_no_cache_when_ttl_zero() -> None:
    c = SsiDataClient(consumer_id="x", consumer_secret="y", url="http://t", cache_ttl_seconds=0)
    calls: list[str] = []

    def fake(method: str, build_req) -> dict:
        calls.append(method)
        return {"status": 200, "data": []}

    c._sync_call = fake  # type: ignore[method-assign]
    await c.securities("HOSE")
    await c.securities("HOSE")
    assert calls == ["securities", "securities"]


async def test_data_client_wraps_errors() -> None:
    c = SsiDataClient(consumer_id="x", consumer_secret="y", url="http://t")

    def boom(method: str, build_req) -> dict:
        raise RuntimeError("nope")

    c._sync_call = boom  # type: ignore[method-assign]
    with pytest.raises(SsiError):
        await c.daily_ohlc("VNM", "01/01/2024", "02/01/2024")


def test_trading_client_exposes_only_read_methods() -> None:
    """The hard guarantee: no order-placement / write verb on the facade."""
    public = {n for n in dir(SsiTradingClient) if not n.startswith("_")}
    allowed = {
        "account_id",
        "stock_position",
        "cash_balance",
        "derivative_position",
        "derivative_balance",
        "order_book",
        "order_history",
        "account_info",
    }
    assert public == allowed, f"unexpected public surface: {public ^ allowed}"
