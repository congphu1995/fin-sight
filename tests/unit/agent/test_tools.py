"""Unit tests for tools that don't require Postgres.

DB-touching tools (search_reports, get_report_metrics) are exercised through
docker-compose integration tests. `ask_report_pdf` touches the DB via session
but its non-DB branches (Gemini errors, missing PDF) are unit-testable with
a mocked session.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest

from app.agent.tools.ask_report_pdf import AskReportPdf, AskReportPdfArgs
from app.agent.tools.base import ToolContext
from app.agent.tools.fetch_url import FetchUrl, FetchUrlArgs
from app.agent.tools.web_search import WebSearch, WebSearchArgs
from app.core.exceptions import LLMError
from app.core.llm.gemini import ToolUseResponse
from app.reports.models import Report


def _ctx(gemini=None, minio=None) -> ToolContext:
    return ToolContext(
        session=MagicMock(),
        minio=minio or MagicMock(),
        gemini=gemini or MagicMock(),
        logger=MagicMock(),
    )


async def test_web_search_returns_text_and_citations() -> None:
    gemini = MagicMock()
    gemini.generate_with_tools = AsyncMock(
        return_value=ToolUseResponse(
            text="latest news",
            citations=[{"uri": "https://example.com", "title": "Example"}],
        )
    )
    out = await WebSearch().run(WebSearchArgs(query="VHM news"), _ctx(gemini=gemini))
    assert out["answer"] == "latest news"
    assert out["citations"] == [{"uri": "https://example.com", "title": "Example"}]
    # Must enable google_search and pass an empty tool list.
    call = gemini.generate_with_tools.await_args
    assert call.kwargs["enable_google_search"] is True
    assert call.kwargs["tools"] == []


async def test_web_search_returns_error_on_exception() -> None:
    gemini = MagicMock()
    gemini.generate_with_tools = AsyncMock(side_effect=RuntimeError("upstream"))
    out = await WebSearch().run(WebSearchArgs(query="x"), _ctx(gemini=gemini))
    assert "error" in out and "upstream" in out["error"]


async def test_fetch_url_strips_html(monkeypatch: pytest.MonkeyPatch) -> None:
    html = b"<html><body><script>x=1</script><h1>Title</h1><p>Body text</p></body></html>"

    class FakeResp:
        status_code = 200
        text = html.decode()
        headers = {"content-type": "text/html; charset=utf-8"}
        url = "https://example.test/page"

        def raise_for_status(self) -> None:
            return None

    class FakeAsyncClient:
        def __init__(self, *a, **kw) -> None: ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a) -> None: return None
        async def get(self, url):
            return FakeResp()

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)

    out = await FetchUrl().run(FetchUrlArgs(url="https://example.test"), _ctx())
    assert "Title" in out["text"]
    assert "Body text" in out["text"]
    assert "x=1" not in out["text"]
    assert out["status"] == 200
    assert out["truncated"] is False


async def test_fetch_url_returns_error_on_http_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingClient:
        def __init__(self, *a, **kw) -> None: ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a) -> None: return None
        async def get(self, url):
            raise httpx.ConnectError("dns fail")

    monkeypatch.setattr(httpx, "AsyncClient", FailingClient)

    out = await FetchUrl().run(FetchUrlArgs(url="https://nope.test"), _ctx())
    assert "error" in out and "dns fail" in out["error"]


async def test_ask_report_pdf_calls_gemini_with_pdf_bytes() -> None:
    report = Report(
        id=uuid4(),
        source_id=1,
        report_type_id=1,
        external_id="ext",
        ticker="HPG",
        title="HPG Q3 Update",
        status="extracted",
        pdf_object_key="reports/HPG/x.pdf",
    )
    session = MagicMock()
    session.get = AsyncMock(return_value=report)
    minio = MagicMock()
    minio.get_object = AsyncMock(return_value=b"%PDF-fake")
    gemini = MagicMock()
    gemini.ask_about_pdf = AsyncMock(return_value="The target price is 30,000 VND.")

    out = await AskReportPdf().run(
        AskReportPdfArgs(report_id=report.id, query="What is the target price?"),
        _ctx(gemini=gemini, minio=minio).__class__(
            session=session, minio=minio, gemini=gemini, logger=MagicMock()
        ),
    )

    assert out["answer"] == "The target price is 30,000 VND."
    assert out["ticker"] == "HPG"
    gemini.ask_about_pdf.assert_awaited_once_with(b"%PDF-fake", "What is the target price?")


async def test_ask_report_pdf_returns_error_when_report_missing() -> None:
    session = MagicMock()
    session.get = AsyncMock(return_value=None)
    ctx = ToolContext(session=session, minio=MagicMock(), gemini=MagicMock(), logger=MagicMock())

    out = await AskReportPdf().run(
        AskReportPdfArgs(report_id=uuid4(), query="x"), ctx
    )
    assert "error" in out and "not found" in out["error"]


async def test_ask_report_pdf_returns_error_on_llm_failure() -> None:
    report = Report(
        id=uuid4(),
        source_id=1,
        report_type_id=1,
        external_id="ext",
        ticker="HPG",
        title="HPG",
        status="extracted",
        pdf_object_key="reports/HPG/x.pdf",
    )
    session = MagicMock()
    session.get = AsyncMock(return_value=report)
    minio = MagicMock()
    minio.get_object = AsyncMock(return_value=b"%PDF-fake")
    gemini = MagicMock()
    gemini.ask_about_pdf = AsyncMock(side_effect=LLMError("upstream"))
    ctx = ToolContext(session=session, minio=minio, gemini=gemini, logger=MagicMock())

    out = await AskReportPdf().run(
        AskReportPdfArgs(report_id=report.id, query="x"), ctx
    )
    assert "error" in out and "upstream" in out["error"]
