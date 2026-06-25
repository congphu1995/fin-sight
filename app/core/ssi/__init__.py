"""SSI FastConnect clients (Tier 2, live market + personal account data).

- `SsiDataClient`    — FastConnect Data: market data (non-personal).
- `SsiTradingClient` — FastConnect Trading: YOUR account, READ-ONLY.

Both wrap the official sync SSI SDKs behind an async facade (asyncio.to_thread),
mirroring `app/core/storage/minio_client.py`. The SDKs manage access-token
refresh internally; we add lazy construction, a serialization lock, and a
short-TTL response cache.
"""

from app.core.ssi.data_client import SsiDataClient
from app.core.ssi.trading_client import SsiTradingClient

__all__ = ["SsiDataClient", "SsiTradingClient"]
