"""Async facade over the SSI FastConnect Data SDK (`ssi_fc_data`) — market data.

The SDK is sync (requests-based) and its client constructor performs a network
call (it fetches an access token), so we build it lazily inside a worker thread
and serialize access behind a lock. A short-TTL cache cuts per-connection-key
rate-limit pressure; the SDK refreshes the access token internally on expiry.

Dates are SSI's `dd/mm/yyyy` strings. Every method returns the SDK's raw JSON
dict ({"status", "message", "data": [...]}); shaping to text happens in the tool.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import SsiError


@dataclass
class _DataConfig:
    # Attribute names match what ssi_fc_data.MarketDataClient reads off `config`.
    url: str
    consumerID: str  # noqa: N815 — SDK-mandated attribute name
    consumerSecret: str  # noqa: N815 — SDK-mandated attribute name


class SsiDataClient:
    def __init__(
        self,
        *,
        consumer_id: str,
        consumer_secret: str,
        url: str,
        cache_ttl_seconds: float = 60.0,
    ) -> None:
        self._cfg = _DataConfig(url=url, consumerID=consumer_id, consumerSecret=consumer_secret)
        self._cache_ttl = cache_ttl_seconds
        self._lock = asyncio.Lock()
        self._client: Any = None
        self._cache: dict[tuple, tuple[float, Any]] = {}

    def _sync_call(self, method: str, build_req: Callable[[Any], Any]) -> Any:
        from ssi_fc_data import fc_md_client
        from ssi_fc_data.model import model

        if self._client is None:
            self._client = fc_md_client.MarketDataClient(self._cfg)
        req = build_req(model)
        # SDK signature is (unused_input, request_object); pass the config for the first arg.
        return getattr(self._client, method)(self._cfg, req)

    async def _call(self, method: str, key: tuple, build_req: Callable[[Any], Any]) -> Any:
        async with self._lock:
            hit = self._cache.get(key)
            if hit is not None and (time.monotonic() - hit[0]) < self._cache_ttl:
                return hit[1]
            try:
                result = await asyncio.to_thread(self._sync_call, method, build_req)
            except Exception as exc:
                raise SsiError(f"SSI FC Data {method} failed: {exc}") from exc
            self._cache[key] = (time.monotonic(), result)
            return result

    async def daily_ohlc(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
        page_index: int = 1,
        page_size: int = 100,
        ascending: bool = True,
    ) -> Any:
        return await self._call(
            "daily_ohlc",
            ("daily_ohlc", symbol, from_date, to_date, page_index, page_size, ascending),
            lambda m: m.daily_ohlc(
                symbol=symbol,
                fromDate=from_date,
                toDate=to_date,
                pageIndex=page_index,
                pageSize=page_size,
                ascending=ascending,
            ),
        )

    async def securities(self, market: str, page_index: int = 1, page_size: int = 1000) -> Any:
        return await self._call(
            "securities",
            ("securities", market, page_index, page_size),
            lambda m: m.securities(market=market, pageIndex=page_index, pageSize=page_size),
        )

    async def index_components(
        self, index_code: str, page_index: int = 1, page_size: int = 100
    ) -> Any:
        return await self._call(
            "index_components",
            ("index_components", index_code, page_index, page_size),
            lambda m: m.index_components(
                indexCode=index_code, pageIndex=page_index, pageSize=page_size
            ),
        )

    async def daily_stock_price(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
        page_index: int = 1,
        page_size: int = 100,
        market: str = "",
    ) -> Any:
        return await self._call(
            "daily_stock_price",
            ("daily_stock_price", symbol, from_date, to_date, page_index, page_size, market),
            lambda m: m.daily_stock_price(
                symbol=symbol,
                fromDate=from_date,
                toDate=to_date,
                pageIndex=page_index,
                pageSize=page_size,
                market=market,
            ),
        )
