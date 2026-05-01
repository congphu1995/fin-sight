"""Unit-level coverage of the extractor's hot-column promotion logic."""

from app.reports.services.extractor import _coerce_hot_value, _extract_facets


def test_coerce_target_price_string() -> None:
    from decimal import Decimal

    assert _coerce_hot_value("target_price", "36600") == Decimal("36600")


def test_coerce_target_price_none() -> None:
    assert _coerce_hot_value("target_price", None) is None


def test_coerce_summary_passthrough() -> None:
    assert _coerce_hot_value("summary", "abc") == "abc"


def test_facets_industry() -> None:
    payload = {
        "industry": "Steel",
        "outlook": "POSITIVE",
        "top_picks": [{"ticker": "hpg"}, {"ticker": "HSG"}, {"ticker": " hpg "}],
    }
    out = _extract_facets(payload, "industry", report_ticker=None)
    assert out["industry_name"] == "Steel"
    assert out["outlook"] == "POSITIVE"
    assert out["mentioned_tickers"] == ["HPG", "HSG"]


def test_facets_industry_invalid_outlook_dropped() -> None:
    out = _extract_facets({"industry": "X", "outlook": "MAYBE"}, "industry", None)
    assert "outlook" not in out
    assert out["industry_name"] == "X"


def test_facets_macro() -> None:
    out = _extract_facets(
        {"period": "Q1 2026", "market_outlook": "NEUTRAL"}, "macro", None
    )
    assert out == {"period": "Q1 2026", "outlook": "NEUTRAL"}


def test_facets_technical() -> None:
    payload = {
        "period": "May 2026",
        "top_signals": [{"ticker": "vcb"}],
        "index_outlook": [{"symbol": "vnindex"}],
    }
    out = _extract_facets(payload, "technical", None)
    assert out["period"] == "May 2026"
    assert sorted(out["mentioned_tickers"]) == ["VCB", "VNINDEX"]


def test_facets_thematic() -> None:
    payload = {
        "topic": "EV transition",
        "affected_tickers": [{"ticker": "VEA"}, {"ticker": "TMT"}],
    }
    out = _extract_facets(payload, "thematic", None)
    assert out["topic"] == "EV transition"
    assert out["mentioned_tickers"] == ["VEA", "TMT"]


def test_facets_company_uses_report_ticker() -> None:
    out = _extract_facets({}, "company", report_ticker="hpg")
    assert out == {"mentioned_tickers": ["HPG"]}


def test_facets_company_no_ticker() -> None:
    assert _extract_facets({}, "company", report_ticker=None) == {}


def test_facets_generic_empty() -> None:
    assert _extract_facets({"summary": "..."}, "generic", None) == {}


def test_facets_industry_empty_top_picks() -> None:
    out = _extract_facets({"industry": "Banks", "top_picks": []}, "industry", None)
    assert out == {"industry_name": "Banks"}
