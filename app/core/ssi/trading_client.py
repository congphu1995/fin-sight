"""Async facade over the SSI FastConnect Trading SDK (`ssi_fctrading`) — READ-ONLY.

Exposes ONLY account-query methods (positions, balances, orders). It NEVER calls
``verifyCode`` / ``new_order`` / ``modify_order`` / ``cancle_order`` / ``create_*``.
In the SDK those need a separate *write* access token — minted only by
``verifyCode(pin)`` — plus an RSA signature; since this facade never mints it, no
order can be placed even if the underlying SDK object is reached. Reads use the
SDK's *read* token, obtained from consumer id/secret with no 2FA code.

The hard guarantee: the only public methods here are reads. A test asserts this
facade exposes no write verb. (See CLAUDE.md → SSI.)

Sync SDK → built lazily in a worker thread (its constructor does network + reads
the PEM), serialized behind a lock, short-TTL response cache.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.exceptions import SsiError


def _read_pem(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


class SsiTradingClient:
    def __init__(
        self,
        *,
        consumer_id: str,
        consumer_secret: str,
        private_key_path: str,
        account_id: str,
        url: str,
        two_fa_type: int = 0,
        cache_ttl_seconds: float = 60.0,
    ) -> None:
        self._consumer_id = consumer_id
        self._consumer_secret = consumer_secret
        self._private_key_path = private_key_path
        self._account = account_id
        self._url = url
        self._two_fa_type = two_fa_type
        self._cache_ttl = cache_ttl_seconds
        self._lock = asyncio.Lock()
        self._client: Any = None
        self._cache: dict[tuple, tuple[float, Any]] = {}

    @property
    def account_id(self) -> str:
        return self._account

    def _sync_call(self, method: str, build_req: Callable[[Any], Any] | None) -> Any:
        from ssi_fctrading import FCTradingClient
        from ssi_fctrading.models import fcmodel_requests as req

        if self._client is None:
            private_key = _read_pem(self._private_key_path)
            self._client = FCTradingClient(
                self._url,
                self._consumer_id,
                self._consumer_secret,
                private_key,
                self._two_fa_type,
            )
        fn = getattr(self._client, method)
        return fn(build_req(req)) if build_req is not None else fn()

    async def _call(self, method: str, key: tuple, build_req: Callable[[Any], Any] | None) -> Any:
        async with self._lock:
            hit = self._cache.get(key)
            if hit is not None and (time.monotonic() - hit[0]) < self._cache_ttl:
                return hit[1]
            try:
                result = await asyncio.to_thread(self._sync_call, method, build_req)
            except Exception as exc:
                raise SsiError(f"SSI FC Trading {method} failed: {exc}") from exc
            self._cache[key] = (time.monotonic(), result)
            return result

    # --- READ methods only ---

    async def stock_position(self) -> Any:
        return await self._call(
            "get_stock_position",
            ("stock_position", self._account),
            lambda r: r.StockPosition(self._account),
        )

    async def cash_balance(self) -> Any:
        return await self._call(
            "get_stock_account_balance",
            ("cash_balance", self._account),
            lambda r: r.StockAccountBalance(self._account),
        )

    async def derivative_position(self) -> Any:
        return await self._call(
            "get_derivative_position",
            ("deriv_position", self._account),
            lambda r: r.DerivativePosition(self._account, True),
        )

    async def derivative_balance(self) -> Any:
        return await self._call(
            "get_derivative_account_balance",
            ("deriv_balance", self._account),
            lambda r: r.DerivativeAccountBalance(self._account),
        )

    async def order_book(self) -> Any:
        return await self._call(
            "get_order_book",
            ("order_book", self._account),
            lambda r: r.OrderBook(self._account),
        )

    async def order_history(self, start_date: str, end_date: str) -> Any:
        return await self._call(
            "get_order_history",
            ("order_history", self._account, start_date, end_date),
            lambda r: r.OrderHistory(self._account, start_date, end_date),
        )

    async def account_info(self) -> Any:
        return await self._call(
            "get_pp_mmr_account",
            ("pp_mmr", self._account),
            lambda r: r.PPMMRAccount(self._account),
        )
