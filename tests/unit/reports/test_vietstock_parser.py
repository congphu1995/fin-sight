"""Unit tests for the Vietstock listing-page card parser."""

from datetime import date
from pathlib import Path

from app.reports.crawlers.vietstock import _parse_cards

FIXTURE_DIR = Path(__file__).parents[2] / "fixtures" / "vietstock"


def test_parse_cards_extracts_featured_and_grid() -> None:
    html = (FIXTURE_DIR / "type_58_page1.html").read_text(encoding="utf-8")
    cards = _parse_cards(html, source_code="vietstock", type_external_id="58")

    by_id = {c.external_id: c for c in cards}
    assert set(by_id) == {"19965", "19941"}

    first = by_id["19965"]
    assert first.ticker == "HPG"
    assert first.title.startswith("HPG: Khuyến nghị MUA")
    assert first.publisher == "Vietcap"
    assert first.published_at == date(2026, 4, 23)
    assert first.pdf_url == "https://finance.vietstock.vn/downloadedoc/19965"
    assert first.detail_url and first.detail_url.startswith("https://finance.vietstock.vn/")

    second = by_id["19941"]
    assert second.publisher == "SSI"
    assert second.published_at == date(2026, 4, 20)
    assert second.ticker == "HPG"


def test_parse_cards_empty_html_returns_empty() -> None:
    assert _parse_cards("", source_code="vietstock", type_external_id="58") == []
