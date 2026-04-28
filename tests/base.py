"""Test doubles. No fixtures here — those live in the relevant conftest.py."""

from collections.abc import AsyncIterator
from datetime import date

from pydantic import BaseModel

from app.reports.crawlers.base import DiscoveredReport, ReportSource


class FakeGeminiClient:
    """Test double for GeminiClient — returns canned answers; records prompts."""

    def __init__(self, answer: str = "fake-answer") -> None:
        self.answer = answer
        self.prompts: list[str] = []
        self.pdf_responses: dict[type[BaseModel], BaseModel] = {}
        self.pdf_calls: list[tuple[bytes, str, type[BaseModel]]] = []

    async def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.answer

    async def generate_from_pdf(
        self, pdf_bytes: bytes, prompt: str, response_schema: type[BaseModel]
    ) -> BaseModel:
        self.pdf_calls.append((pdf_bytes, prompt, response_schema))
        canned = self.pdf_responses.get(response_schema)
        if canned is None:
            # Default: instantiate with minimum required fields. Tests can override
            # by setting fake.pdf_responses[CompanyExtraction] = CompanyExtraction(...).
            return response_schema.model_validate({"summary": "fake-summary"})
        return canned


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
