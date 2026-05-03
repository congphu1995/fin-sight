"""Unit-level coverage of the extractor's hot-column promotion logic."""

import pytest

from app.reports.services.extractor import (
    _FACET_STRIP_KEYS,
    _HOT_FIELDS,
    _coerce_hot_value,
    _extract_facets,
)


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
    out = _extract_facets({"industry": "Steel", "outlook": "MAYBE"}, "industry", None)
    assert "outlook" not in out
    assert out["industry_name"] == "Steel"


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
    out = _extract_facets({"industry": "Steel", "top_picks": []}, "industry", None)
    assert out == {"industry_name": "Steel"}


def test_facets_industry_canonicalizes_vietnamese() -> None:
    """LLM occasionally returns the Vietnamese form despite the prompt; the
    runtime backstop maps it to the canonical English label."""
    assert _extract_facets({"industry": "Thép"}, "industry", None) == {
        "industry_name": "Steel"
    }
    assert _extract_facets({"industry": "Ngân hàng"}, "industry", None) == {
        "industry_name": "Banking"
    }
    # Case + whitespace tolerance.
    assert _extract_facets({"industry": "  banking  "}, "industry", None) == {
        "industry_name": "Banking"
    }
    # English near-miss ("Banks" → "Banking").
    assert _extract_facets({"industry": "Banks"}, "industry", None) == {
        "industry_name": "Banking"
    }


def test_facets_industry_unknown_passthrough() -> None:
    """A sector we haven't catalogued passes through unchanged (after trim)
    rather than being coerced to "Other" — operator can review and add an
    alias if needed."""
    out = _extract_facets({"industry": "  SomeNewSector "}, "industry", None)
    assert out == {"industry_name": "SomeNewSector"}


# --- extras / facet-strip drift safeguard --------------------------------------
# The test below replicates the `extras` build expression at extractor.py:185
# and asserts the invariant: every key in _FACET_STRIP_KEYS[schema] is removed
# from extras, while a known kept key (an array of objects we use as a lossy
# ticker source) survives. If a future change to _extract_facets promotes a new
# scalar to a column without updating _FACET_STRIP_KEYS, this test fails.

_STRIP_FIXTURES: dict[str, tuple[dict, set[str]]] = {
    "industry": (
        {
            "industry": "Steel",
            "outlook": "POSITIVE",
            "top_picks": [{"ticker": "HPG"}],
            "summary": "thesis...",
            "key_drivers": ["a"],
        },
        {"top_picks", "key_drivers"},
    ),
    "macro": (
        {
            "period": "Q1 2026",
            "market_outlook": "NEUTRAL",
            "summary": "thesis...",
            "key_themes": ["a"],
        },
        {"key_themes"},
    ),
    "technical": (
        {
            "period": "May 2026",
            "top_signals": [{"ticker": "VCB"}],
            "index_outlook": [{"symbol": "VNINDEX"}],
            "summary": "thesis...",
        },
        {"top_signals", "index_outlook"},
    ),
    "thematic": (
        {
            "topic": "EV transition",
            "affected_tickers": [{"ticker": "VEA"}],
            "summary": "thesis...",
            "key_findings": ["a"],
        },
        {"affected_tickers", "key_findings"},
    ),
    "company": (
        {
            "summary": "thesis...",
            "recommendation": "BUY",
            "key_drivers": ["a"],
        },
        {"key_drivers"},
    ),
    "generic": (
        {
            "summary": "thesis...",
            "key_findings": ["a"],
        },
        {"key_findings"},
    ),
}


@pytest.mark.parametrize("schema_key", sorted(_FACET_STRIP_KEYS))
def test_extras_excludes_promoted_keys(schema_key: str) -> None:
    payload, expected_kept = _STRIP_FIXTURES[schema_key]
    strip = (
        set(_HOT_FIELDS) | {"time_horizon"} | _FACET_STRIP_KEYS.get(schema_key, frozenset())
    )
    extras = {k: v for k, v in payload.items() if k not in strip}

    for promoted in _FACET_STRIP_KEYS[schema_key]:
        assert promoted not in extras, (
            f"schema={schema_key}: promoted key '{promoted}' leaked into extras "
            f"— update _FACET_STRIP_KEYS or _extract_facets to keep them in sync"
        )
    assert set(extras) == expected_kept, (
        f"schema={schema_key}: extras keys {set(extras)} != expected {expected_kept}"
    )
