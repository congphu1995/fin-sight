"""Verify the tool registry is consistent and rejects duplicates."""

from datetime import date

import pytest
from pydantic import BaseModel

from app.agent.tools import TOOL_REGISTRY, Tool, register
from app.agent.tools.search_reports import SearchReports, SearchReportsArgs


def test_required_tools_are_registered() -> None:
    expected = {
        "search_reports",
        "get_report_metrics",
        "web_search",
        "fetch_url",
        "ask_report_pdf",
    }
    assert expected.issubset(TOOL_REGISTRY)


def test_each_registered_tool_has_required_attributes() -> None:
    for name, tool in TOOL_REGISTRY.items():
        assert tool.name == name
        assert tool.description, f"{name} has no description"
        assert issubclass(tool.args_schema, BaseModel), f"{name}.args_schema is not pydantic"


def test_search_reports_args_validate() -> None:
    # All optional except limit (which has a default).
    args = SearchReportsArgs.model_validate(
        {"ticker": "HPG", "since": "2024-01-01", "until": "2024-12-31", "limit": 5}
    )
    assert args.ticker == "HPG"
    assert args.since == date(2024, 1, 1)
    assert args.limit == 5


def test_search_reports_args_reject_oversized_limit() -> None:
    with pytest.raises(ValueError):
        SearchReportsArgs.model_validate({"limit": 999})


def test_register_rejects_duplicates() -> None:
    class DupeTool(Tool):
        name = "search_reports"
        description = "x"
        args_schema = SearchReportsArgs

        async def run(self, args, ctx):  # type: ignore[override]
            raise NotImplementedError

    with pytest.raises(RuntimeError):
        register(DupeTool)


def test_search_reports_class_carries_metadata() -> None:
    assert SearchReports.name == "search_reports"
    assert SearchReports.args_schema is SearchReportsArgs
