"""CLI shell for the reports pipeline.

    python -m app.reports                            # full pipeline, all enabled (source, type)
    python -m app.reports --source vietstock         # one source
    python -m app.reports --type company --ticker HPG
    python -m app.reports --skip-extraction          # discover + download only
    python -m app.reports --only=extract             # re-extract pending downloads
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import structlog

from app.core.config import get_settings
from app.core.logging.setup import configure_logging
from app.dependencies import get_gemini, get_minio_client, get_session_factory
from app.reports.jobs import Stage, run_pipeline


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m app.reports", description=__doc__)
    p.add_argument("--source", help="Source code (e.g. 'vietstock'). Default: all enabled.")
    p.add_argument(
        "--type",
        dest="type_code",
        help="Report type code (e.g. 'company'). Default: all enabled for the source.",
    )
    p.add_argument(
        "--ticker",
        help="Ticker filter (only honored for ticker_indexed types like 'company').",
    )
    p.add_argument(
        "--backfill-days",
        type=int,
        default=None,
        help="Lookback window in days. Default: settings.crawl_default_lookback_days.",
    )
    p.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Run discover + download only.",
    )
    p.add_argument(
        "--only",
        choices=["discover", "download", "extract"],
        help="Run a single stage. Useful after a prompt-version bump.",
    )
    return p.parse_args(argv)


def stages_from_args(args: argparse.Namespace) -> tuple[Stage, ...]:
    if args.only:
        return (args.only,)  # type: ignore[return-value]
    if args.skip_extraction:
        return ("discover", "download")
    return ("discover", "download", "extract")


async def amain(argv: list[str]) -> int:
    args = parse_args(argv)
    settings = get_settings()
    configure_logging(env=settings.env, level=settings.log_level)
    log = structlog.get_logger()

    session_factory = get_session_factory()
    minio = get_minio_client()
    gemini = get_gemini()

    log.info(
        "jobs.start",
        source=args.source,
        report_type=args.type_code,
        ticker=args.ticker,
        stages=list(stages_from_args(args)),
    )
    results = await run_pipeline(
        session_factory=session_factory,
        settings=settings,
        minio=minio,
        gemini=gemini,
        source_code=args.source,
        type_code=args.type_code,
        ticker=args.ticker,
        backfill_days=args.backfill_days,
        stages=stages_from_args(args),
        logger=log,
    )
    for (src, rtype), counts in results.items():
        log.info(
            "jobs.summary",
            source=src,
            report_type=rtype,
            discovered=counts.discovered,
            downloaded=counts.downloaded,
            extracted=counts.extracted,
        )
    log.info("jobs.done")
    return 0


def main() -> int:
    return asyncio.run(amain(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main())
