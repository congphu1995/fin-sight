"""Renderers must keep ids inline and never end on an opaque token line
(Mira's Gemini empty-final trigger)."""

from app.mcp.render import (
    render_facets,
    render_search_reports,
    render_ssi_account,
    render_ssi_market,
    render_stock_analysis,
)


def _last(s: str) -> str:
    return s.splitlines()[-1].strip()


def test_stock_analysis_id_inline_not_trailing() -> None:
    p = {
        "ticker": "VNM",
        "count": 1,
        "reports": [
            {
                "report_id": "a1b2c3",
                "title": "Q1 outlook",
                "published_at": "2026-05-01",
                "publisher": "SSI",
                "report_type_code": "company",
                "recommendation": "BUY",
                "target_price": 78000.0,
                "target_currency": "VND",
                "outlook": "POSITIVE",
                "horizon": "12m",
                "summary": "Strong quarter.",
            }
        ],
    }
    out = render_stock_analysis(p)
    assert "a1b2c3" in out  # id present, inline
    assert not _last(out).endswith("a1b2c3")  # never the trailing token


def test_stock_analysis_empty() -> None:
    assert "No extracted" in render_stock_analysis({"ticker": "XYZ", "count": 0, "reports": []})


def test_error_passthrough_single_line() -> None:
    out = render_search_reports({"error": "boom"})
    assert out == "Error: boom"
    assert "\n" not in out


def test_ssi_market_ends_on_prose_count() -> None:
    p = {
        "symbol": "VNM",
        "status": 200,
        "message": "Success",
        "data": [{"TradingDate": "02/01/2024", "Close": 78.5}],
    }
    last = _last(render_ssi_market(p))
    assert last.startswith("(") and last.endswith(")")


def test_ssi_market_no_data() -> None:
    out = render_ssi_market({"symbol": "VNM", "status": 200, "message": "x", "data": []})
    assert "no data" in out.lower()


def test_facets_single_prose_line() -> None:
    out = render_facets(
        {
            "facet": "industry_name",
            "count": 2,
            "values": [{"value": "Steel", "count": 5}, {"value": "Banks", "count": 3}],
        }
    )
    assert out.endswith(".") and "Steel (5)" in out


def test_ssi_account_derivatives_shape() -> None:
    p = {
        "account": "ACC1",
        "positions": {"status": 200, "data": [{"sym": "VN30F1M"}]},
        "balance": {"status": 200, "data": [{"nav": 1000}]},
    }
    out = render_ssi_account(p)
    assert "derivatives" in out.lower()
