"""Test doubles. No fixtures here — those live in the relevant conftest.py."""

from collections.abc import AsyncIterator
from datetime import date
from typing import Any

from pydantic import BaseModel

from app.core.llm.gemini import ToolCall, ToolUseResponse
from app.reports.crawlers.base import DiscoveredReport, ReportSource


class FakeGeminiClient:
    """Test double for GeminiClient — returns canned answers; records prompts.

    For tool-use tests, push scripted ToolUseResponses onto `tool_responses`
    in order. Each call to `generate_with_tools` consumes the next one.
    """

    def __init__(self, answer: str = "fake-answer") -> None:
        self.answer = answer
        self.prompts: list[str] = []
        self.pdf_responses: dict[type[BaseModel], BaseModel] = {}
        self.pdf_calls: list[tuple[bytes, str, type[BaseModel]]] = []
        self.tool_responses: list[ToolUseResponse] = []
        self.tool_calls_log: list[dict[str, Any]] = []

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer

    async def generate_from_pdf(
        self, pdf_bytes: bytes, prompt: str, response_schema: type[BaseModel]
    ) -> BaseModel:
        self.pdf_calls.append((pdf_bytes, prompt, response_schema))
        canned = self.pdf_responses.get(response_schema)
        if canned is None:
            return response_schema.model_validate({"summary": "fake-summary"})
        return canned

    async def generate_with_tools(
        self,
        contents: list[Any],
        tools: list[Any],
        *,
        system_instruction: str | None = None,
        enable_google_search: bool = False,
    ) -> ToolUseResponse:
        self.tool_calls_log.append(
            {
                "contents": contents,
                "tools": [t.name for t in tools],
                "system_instruction": system_instruction,
                "enable_google_search": enable_google_search,
            }
        )
        if not self.tool_responses:
            return ToolUseResponse(text=self.answer)
        return self.tool_responses.pop(0)

    def script_tool_call(
        self, name: str, args: dict[str, Any], call_id: str | None = None
    ) -> None:
        """Helper: append a tool-call response for the next generate_with_tools call."""
        cid = call_id or f"call_{len(self.tool_responses)}"
        self.tool_responses.append(
            ToolUseResponse(tool_calls=[ToolCall(id=cid, name=name, args=args)])
        )

    def script_text(self, text: str) -> None:
        """Helper: append a final-text response."""
        self.tool_responses.append(ToolUseResponse(text=text))


class FakeMinioClient:
    """In-memory MinioClient. Implements MinioClientProtocol."""

    def __init__(self, bucket: str = "test-bucket") -> None:
        self.bucket = bucket
        self.objects: dict[str, bytes] = {}

    async def put_object(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> None:
        self.objects[key] = data

    async def get_object(self, key: str) -> bytes:
        return self.objects[key]

    async def stat_object(self, key: str) -> bool:
        return key in self.objects

    async def presigned_get_url(self, key: str, expires_seconds: int = 3600) -> str:
        return f"https://fake-minio/{self.bucket}/{key}?expires={expires_seconds}"

    async def ensure_bucket(self) -> None:
        return None


class FakeReportSource(ReportSource):
    """Yields a fixed list of DiscoveredReports; returns canned bytes for fetch_pdf."""

    code = "vietstock"
    name = "Vietstock (fake)"
    base_url = "https://example.test"

    def __init__(
        self,
        items: list[DiscoveredReport],
        pdf_by_external_id: dict[str, bytes] | None = None,
    ) -> None:
        self._items = items
        self._pdfs = pdf_by_external_id or {}
        self.fetch_calls: list[str] = []

    async def discover(
        self,
        type_code: str,
        since: date,
        until: date,
        ticker: str | None = None,
    ) -> AsyncIterator[DiscoveredReport]:
        for item in self._items:
            if item.type_code != type_code:
                continue
            if ticker and item.ticker != ticker:
                continue
            yield item

    async def fetch_pdf(self, report: DiscoveredReport) -> bytes:
        self.fetch_calls.append(report.external_id)
        return self._pdfs.get(report.external_id, b"%PDF-fake")
