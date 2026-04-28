"""Unit-level coverage of crawler abstractions."""

from app.reports.crawlers.base import SOURCE_REGISTRY


def test_vietstock_is_registered() -> None:
    assert "vietstock" in SOURCE_REGISTRY
    cls = SOURCE_REGISTRY["vietstock"]
    assert cls.code == "vietstock"
    assert cls.name == "Vietstock"


def test_register_rejects_duplicates() -> None:
    import pytest

    from app.reports.crawlers.base import ReportSource, register

    class DupeSource(ReportSource):
        code = "vietstock"
        name = "Dup"
        base_url = "x"

        def discover(self, type_code, since, until, ticker=None):  # type: ignore[override]
            raise NotImplementedError

        async def fetch_pdf(self, report):  # type: ignore[override]
            raise NotImplementedError

    with pytest.raises(RuntimeError):
        register(DupeSource)
