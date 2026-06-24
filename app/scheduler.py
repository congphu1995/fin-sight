"""In-process background refresh (Tier 1).

Periodically runs the reports pipeline so the DB stays fresh without an external
cron. Mirrors the manual `python -m app.reports` path. One instance per process
(single-owner); the pipeline's idempotent stages make an overlapping/missed tick
harmless. `refresh_interval_hours <= 0` disables it (e.g. when a cron drives it).
"""

from __future__ import annotations

import asyncio
import contextlib

import structlog

from app.core.config import Settings
from app.dependencies import get_gemini, get_minio_client, get_session_factory
from app.reports.jobs import run_pipeline


class ReportsScheduler:
    def __init__(
        self, settings: Settings, logger: structlog.stdlib.BoundLogger | None = None
    ) -> None:
        self._settings = settings
        self._log = logger or structlog.get_logger()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._settings.refresh_interval_hours <= 0:
            self._log.info("scheduler.disabled")
            return
        self._task = asyncio.create_task(self._loop(), name="reports-refresh")
        self._log.info("scheduler.started", interval_hours=self._settings.refresh_interval_hours)

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _loop(self) -> None:
        interval = self._settings.refresh_interval_hours * 3600.0
        if self._settings.refresh_on_startup:
            await self._run_once()
        while not self._stop.is_set():
            with contextlib.suppress(TimeoutError):
                # Wake early if asked to stop; otherwise tick after `interval`.
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            if self._stop.is_set():
                break
            await self._run_once()

    async def _run_once(self) -> None:
        try:
            results = await asyncio.wait_for(
                run_pipeline(
                    session_factory=get_session_factory(),
                    settings=self._settings,
                    minio=get_minio_client(),
                    gemini=get_gemini(),
                    logger=self._log,
                ),
                timeout=self._settings.refresh_timeout_seconds,
            )
            self._log.info(
                "scheduler.refresh.done",
                discovered=sum(c.discovered for c in results.values()),
                downloaded=sum(c.downloaded for c in results.values()),
                extracted=sum(c.extracted for c in results.values()),
            )
        except TimeoutError:
            self._log.warning(
                "scheduler.refresh.timeout", timeout=self._settings.refresh_timeout_seconds
            )
        except Exception:
            self._log.exception("scheduler.refresh.failed")
