"""QA agent — multi-turn Q&A over the report catalogue + public web.

This is the agent that backs the original `/chat` endpoint.
"""

from pathlib import Path

from app.agent.agents.base import AgentSpec, register_agent

_PROMPT = (Path(__file__).parent / "prompt.md").read_text(encoding="utf-8")

QA_AGENT = register_agent(
    AgentSpec(
        key="qa",
        description="Q&A research assistant for Vietnamese-equity analysts.",
        system_prompt=_PROMPT,
        tool_names=(
            "search_reports",
            "list_facets",
            "get_report_metrics",
            "ask_report_pdf",
            "web_search",
            "fetch_url",
        ),
    )
)
