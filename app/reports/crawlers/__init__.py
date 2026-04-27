# Importing the implementations triggers their @register decorators.
from app.reports.crawlers import vietstock  # noqa: F401
from app.reports.crawlers.base import (
    SOURCE_REGISTRY,
    DiscoveredReport,
    ReportSource,
    register,
)

__all__ = ["SOURCE_REGISTRY", "DiscoveredReport", "ReportSource", "register"]
