"""Vietstock — finance.vietstock.vn analyst-report crawler.

Listing: POST /View/ChannelEDocumentPage with reportTypeID + (optional) keyword=<ticker>.
- pageSize is server-capped at 20.
- An anti-CSRF token is fetched from a hidden input on the listing page and replayed.
- HTML structure: .edoc-first (top featured) + .edoc-child (grid items).
"""

import asyncio
import contextlib
import re
from collections.abc import AsyncIterator
from datetime import date, datetime
from typing import ClassVar

import httpx
from bs4 import BeautifulSoup, Tag

from app.core.exceptions import CrawlerError
from app.reports.crawlers.base import DiscoveredReport, ReportSource, register

REPORT_ID_RE = re.compile(r"/bao-cao-phan-tich/(\d+)/")
DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})")


@register
class VietstockSource(ReportSource):
    code = "vietstock"
    name = "Vietstock"
    base_url = "https://finance.vietstock.vn"

    LISTING_URL = f"{base_url}/bao-cao-phan-tich/phan-tich-doanh-nghiep"
    API_URL = f"{base_url}/View/ChannelEDocumentPage"
    PAGE_SIZE = 20  # server-capped

    # Universal type code → Vietstock's `reportTypeID` query value.
    # Adding a new Vietstock type = add a line here + INSERT into report_types.
    TYPE_FILTER: ClassVar[dict[str, str]] = {
        "technical": "49",
        "macro": "51",
        "industry": "57",
        "company": "58",
        "thematic": "59",
    }

    def __init__(
        self,
        http: httpx.AsyncClient,
        request_delay_seconds: float = 1.0,
        max_pages: int = 50,
    ) -> None:
        self._http = http
        self._delay = request_delay_seconds
        self._max_pages = max_pages
        self._token: str | None = None

    async def _fetch_token(self) -> str:
        if self._token:
            return self._token
        try:
            r = await self._http.get(self.LISTING_URL)
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise CrawlerError(f"vietstock token fetch: {exc}") from exc
        soup = BeautifulSoup(r.text, "lxml")
        inp = soup.select_one('input[name="__RequestVerificationToken"]')
        token = inp.get("value") if inp else None
        if not token:
            raise CrawlerError("vietstock: __RequestVerificationToken not found on listing page")
        self._token = token
        return token

    async def discover(
        self,
        type_code: str,
        since: date,
        until: date,
        ticker: str | None = None,
    ) -> AsyncIterator[DiscoveredReport]:
        report_type_id = self.TYPE_FILTER.get(type_code)
        if report_type_id is None:
            raise CrawlerError(
                f"vietstock has no mapping for type_code {type_code!r}; "
                f"known: {sorted(self.TYPE_FILTER)}"
            )
        token = await self._fetch_token()
        seen: set[str] = set()
        for page in range(1, self._max_pages + 1):
            data = {
                "keyword": ticker or "",
                "fromdate": since.isoformat(),
                "todate": until.isoformat(),
                "pageSize": str(self.PAGE_SIZE),
                "__RequestVerificationToken": token,
                "reportTypeID": report_type_id,
                "sourceID": "0",
                "page": str(page),
            }
            try:
                r = await self._http.post(self.API_URL, data=data)
                r.raise_for_status()
            except httpx.HTTPError as exc:
                raise CrawlerError(f"vietstock listing page {page}: {exc}") from exc

            cards = list(
                _parse_cards(r.text, source_code=self.code, type_code=type_code)
            )
            if not cards:
                return
            new = [c for c in cards if c.external_id not in seen]
            if not new:
                return
            for card in new:
                seen.add(card.external_id)
                yield card
            await asyncio.sleep(self._delay)

    async def fetch_pdf(self, report: DiscoveredReport) -> bytes:
        url = report.pdf_url or f"{self.base_url}/downloadedoc/{report.external_id}"
        try:
            r = await self._http.get(url, follow_redirects=True, timeout=60.0)
            r.raise_for_status()
        except httpx.HTTPError as exc:
            raise CrawlerError(f"vietstock fetch_pdf {report.external_id}: {exc}") from exc
        return r.content


def _parse_cards(html: str, *, source_code: str, type_code: str) -> list[DiscoveredReport]:
    """Each card is `.edoc-first` (top featured, page 1 only) or `.edoc-child` (grid).
    Both have an `a.title-link` for the title and a "Nguồn:" label preceding the source.
    The publication date appears as `dd/MM/yyyy` text inside the card."""
    soup = BeautifulSoup(html, "lxml")
    out: list[DiscoveredReport] = []
    for card in soup.select(".edoc-first, .edoc-child"):
        title_link = card.select_one('a.title-link[href*="/bao-cao-phan-tich/"]')
        if not title_link:
            continue
        href = title_link.get("href", "") or ""
        m = REPORT_ID_RE.search(href)
        if not m:
            continue
        rid = m.group(1)
        title = title_link.get_text(strip=True)

        ticker = None
        ticker_m = re.match(r"^([A-Z0-9]{2,5})\s*:", title)
        if ticker_m:
            ticker = ticker_m.group(1)

        text = card.get_text(separator=" ", strip=True)
        date_m = DATE_RE.search(text)
        published_at: date | None = None
        if date_m:
            with contextlib.suppress(ValueError):
                published_at = datetime.strptime(date_m.group(1), "%d/%m/%Y").date()

        publisher = _extract_publisher(card)

        detail_url = href if href.startswith("http") else f"https://finance.vietstock.vn{href}"
        pdf_url = f"https://finance.vietstock.vn/downloadedoc/{rid}"

        out.append(
            DiscoveredReport(
                source_code=source_code,
                type_code=type_code,
                external_id=rid,
                ticker=ticker,
                title=title,
                publisher=publisher,
                published_at=published_at,
                detail_url=detail_url,
                pdf_url=pdf_url,
            )
        )
    return out


def _extract_publisher(card: Tag) -> str | None:
    """The publisher label looks like `<span>Nguồn: </span><b class="title">SSI</b>`
    on the featured card, and `<span>Nguồn: </span><a class="title-link">SSI</a>`
    on grid cards."""
    for span in card.find_all("span"):
        if "Nguồn:" not in span.get_text():
            continue
        host = span.parent
        if not host:
            continue
        b = host.select_one("b.title")
        if b and b.get_text(strip=True):
            return b.get_text(strip=True)
        a = host.select_one("a")
        if a and a.get_text(strip=True):
            return a.get_text(strip=True)
    return None
