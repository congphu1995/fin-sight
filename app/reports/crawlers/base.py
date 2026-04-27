"""Abstract source interface and a process-global registry.

A `ReportSource` knows how to enumerate its catalogue (`discover`) and how to fetch
the PDF for a given discovery (`fetch_pdf`). The orchestrator never imports
implementations directly — it reads `sources.code` from Postgres, looks up the
class in `SOURCE_REGISTRY`, and calls the abstract methods.

To add a new source: subclass ReportSource, decorate with @register, drop the file
in this package, INSERT into the `sources` table.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date
from typing import ClassVar


@dataclass
class DiscoveredReport:
    """A row produced by `discover()` — enough to upsert into `reports` and later
    fetch the PDF. Source-specific identifiers stay as strings (no source-specific
    fields leak into the orchestrator)."""

    source_code: str
    type_external_id: str
    external_id: str
    ticker: str | None
    title: str
    publisher: str | None
    published_at: date | None
    detail_url: str | None
    pdf_url: str | None


class ReportSource(ABC):
    code: ClassVar[str]
    name: ClassVar[str]
    base_url: ClassVar[str]

    @abstractmethod
    def discover(
        self,
        type_external_id: str,
        since: date,
        until: date,
        ticker: str | None = None,
    ) -> AsyncIterator[DiscoveredReport]:
        """Yield every report this source has for the given type within
        [since, until], optionally filtered by ticker. Implementations must
        not raise on transient errors — they should retry internally and yield
        what they got, OR raise CrawlerError if a hard stop is needed."""

    @abstractmethod
    async def fetch_pdf(self, report: DiscoveredReport) -> bytes:
        """Return the PDF bytes. Raise CrawlerError on non-recoverable failure."""


SOURCE_REGISTRY: dict[str, type[ReportSource]] = {}


def register(cls: type[ReportSource]) -> type[ReportSource]:
    if cls.code in SOURCE_REGISTRY:
        raise RuntimeError(f"duplicate source code {cls.code!r}")
    SOURCE_REGISTRY[cls.code] = cls
    return cls
