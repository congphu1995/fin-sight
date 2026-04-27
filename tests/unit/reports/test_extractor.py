"""Unit-level coverage of the extractor's hot-column promotion logic."""

from app.reports.services.extractor import _coerce_hot_value


def test_coerce_target_price_string() -> None:
    from decimal import Decimal

    assert _coerce_hot_value("target_price", "36600") == Decimal("36600")


def test_coerce_target_price_none() -> None:
    assert _coerce_hot_value("target_price", None) is None


def test_coerce_summary_passthrough() -> None:
    assert _coerce_hot_value("summary", "abc") == "abc"
