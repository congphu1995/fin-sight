"""Stage 3: extract structured data from PDFs via Gemini.

Work query selects status='downloaded'. For each row: fetch PDF from MinIO, look up
the type's extraction schema, run Gemini, INSERT ON CONFLICT (report_id, prompt_version)
DO NOTHING into report_extractions, flip to status='extracted'.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ExtractionError, LLMError, StorageError
from app.core.llm.gemini import GeminiClient
from app.core.storage.minio_client import MinioClientProtocol
from app.reports.extraction import EXTRACTION_REGISTRY
from app.reports.models import Report, ReportExtraction, ReportType, Source

# Hot columns we promote out of the schema's JSON to top-level columns when present.
_HOT_FIELDS = (
    "summary",
    "recommendation",
    "target_price",
    "target_currency",
    "horizon",
)

_OUTLOOK_VALUES = {"POSITIVE", "NEUTRAL", "NEGATIVE"}


def _extract_facets(payload: dict, schema_key: str, report_ticker: str | None) -> dict:
    """Map a parsed extraction payload to the typed facet columns on
    `report_extractions` (industry_name, topic, outlook, period, mentioned_tickers).

    Returns only the keys we want to write — any column not derivable from the
    schema is simply absent and stays NULL in the DB.
    """
    out: dict = {}
    tickers: list[str] = []

    if schema_key == "industry":
        if (v := payload.get("industry")):
            out["industry_name"] = v
        if (v := payload.get("outlook")) in _OUTLOOK_VALUES:
            out["outlook"] = v
        for tp in payload.get("top_picks") or ():
            if isinstance(tp, dict) and (t := tp.get("ticker")):
                tickers.append(t)

    elif schema_key == "macro":
        if (v := payload.get("period")):
            out["period"] = v
        if (v := payload.get("market_outlook")) in _OUTLOOK_VALUES:
            out["outlook"] = v

    elif schema_key == "technical":
        if (v := payload.get("period")):
            out["period"] = v
        for sig in payload.get("top_signals") or ():
            if isinstance(sig, dict) and (t := sig.get("ticker")):
                tickers.append(t)
        for idx in payload.get("index_outlook") or ():
            if isinstance(idx, dict) and (s := idx.get("symbol")):
                tickers.append(s)

    elif schema_key == "thematic":
        if (v := payload.get("topic")):
            out["topic"] = v
        for at in payload.get("affected_tickers") or ():
            if isinstance(at, dict) and (t := at.get("ticker")):
                tickers.append(t)

    elif schema_key == "company":
        if report_ticker:
            tickers.append(report_ticker)

    if tickers:
        # Normalize and dedupe while preserving first-seen order.
        seen: set[str] = set()
        normed: list[str] = []
        for t in tickers:
            n = t.strip().upper()
            if n and n not in seen:
                seen.add(n)
                normed.append(n)
        if normed:
            out["mentioned_tickers"] = normed
    return out


class ExtractorService:
    def __init__(
        self,
        session: AsyncSession,
        minio: MinioClientProtocol,
        gemini: GeminiClient,
        model_name: str,
        logger: structlog.stdlib.BoundLogger,
        max_retries: int = 3,
    ) -> None:
        self._session = session
        self._minio = minio
        self._gemini = gemini
        self._model_name = model_name
        self._logger = logger
        self._max_retries = max_retries

    async def process_pending(
        self,
        source: Source,
        report_type: ReportType | None,
        batch_size: int,
    ) -> int:
        rt_id = report_type.id if report_type else None
        rows = await self._claim_batch(source.id, rt_id, batch_size)
        if not rows:
            return 0

        # We need ReportType info to know which extraction schema to use.
        type_ids = {r.report_type_id for r in rows}
        type_map = await self._load_types(list(type_ids))

        extracted = 0
        for report in rows:
            rtype = type_map.get(report.report_type_id)
            if rtype is None:
                await self._mark_failure(report, "missing report_type")
                continue
            try:
                await self._extract_one(report, rtype)
                extracted += 1
            except (LLMError, StorageError, ExtractionError) as exc:
                await self._mark_failure(report, str(exc))

        await self._session.commit()
        return extracted

    async def _claim_batch(
        self,
        source_id: int,
        report_type_id: int | None,
        batch_size: int,
    ) -> list[Report]:
        stmt = select(Report).where(
            Report.source_id == source_id,
            Report.status == "downloaded",
            Report.retry_count < self._max_retries,
        )
        if report_type_id is not None:
            stmt = stmt.where(Report.report_type_id == report_type_id)
        stmt = stmt.limit(batch_size).with_for_update(skip_locked=True)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _load_types(self, ids: list[int]) -> dict[int, ReportType]:
        if not ids:
            return {}
        result = await self._session.execute(select(ReportType).where(ReportType.id.in_(ids)))
        return {rt.id: rt for rt in result.scalars().all()}

    async def _extract_one(self, report: Report, rtype: ReportType) -> None:
        if not report.pdf_object_key:
            raise ExtractionError(f"report {report.id} has no pdf_object_key")

        defn = EXTRACTION_REGISTRY.get(rtype.code)
        if defn is None:
            defn = EXTRACTION_REGISTRY["generic"]

        pdf_bytes = await self._minio.get_object(report.pdf_object_key)
        parsed = await self._gemini.generate_from_pdf(
            pdf_bytes, defn.prompt_template, defn.schema
        )
        payload = parsed.model_dump(mode="json")

        hot = {f: _coerce_hot_value(f, payload.get(f)) for f in _HOT_FIELDS if f in payload}
        # Schemas spell horizon as "time_horizon" — promote it.
        if "time_horizon" in payload and "horizon" not in hot:
            hot["horizon"] = _coerce_hot_value("horizon", payload.get("time_horizon"))
        extras = {k: v for k, v in payload.items() if k not in _HOT_FIELDS and k != "time_horizon"}
        facets = _extract_facets(payload, defn.key, report.ticker)

        stmt = (
            pg_insert(ReportExtraction)
            .values(
                report_id=report.id,
                model=self._model_name,
                prompt_version=defn.prompt_version,
                summary=hot.get("summary"),
                recommendation=hot.get("recommendation"),
                target_price=hot.get("target_price"),
                target_currency=hot.get("target_currency"),
                horizon=hot.get("horizon"),
                extras=extras,
                raw_response=payload,
                **facets,
            )
            .on_conflict_do_nothing(index_elements=["report_id", "prompt_version"])
        )
        await self._session.execute(stmt)

        await self._session.execute(
            update(Report)
            .where(Report.id == report.id)
            .values(
                status="extracted",
                extracted_at=datetime.now(UTC),
                last_error=None,
            )
        )
        self._logger.info(
            "extractor.extracted",
            report_id=str(report.id),
            external_id=report.external_id,
            schema=defn.key,
            prompt_version=defn.prompt_version,
        )

    async def _mark_failure(self, report: Report, error: str) -> None:
        new_retry = report.retry_count + 1
        new_status = "failed" if new_retry >= self._max_retries else report.status
        await self._session.execute(
            update(Report)
            .where(Report.id == report.id)
            .values(
                retry_count=new_retry,
                last_error=error[:1000],
                status=new_status,
            )
        )
        self._logger.warning(
            "extractor.failure",
            report_id=str(report.id),
            external_id=report.external_id,
            retry_count=new_retry,
            terminal=new_status == "failed",
            error=error[:200],
        )


def _coerce_hot_value(name: str, value: Any) -> Any:
    if value is None:
        return None
    if name == "target_price" and not isinstance(value, Decimal):
        try:
            return Decimal(str(value))
        except Exception:
            return None
    return value
