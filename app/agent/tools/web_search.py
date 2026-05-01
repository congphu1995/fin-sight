from pydantic import BaseModel, Field

from app.agent.tools.base import Tool, ToolContext, register


class WebSearchArgs(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)


@register
class WebSearch(Tool):
    name = "web_search"
    description = (
        "Search the public web for up-to-date information using Google grounding. "
        "Use this for news, market data, or anything that wouldn't be in our "
        "internal reports catalogue. Returns a synthesized answer with citations."
    )
    args_schema = WebSearchArgs

    async def run(self, args: WebSearchArgs, ctx: ToolContext) -> dict:
        # Reuse the existing tool-calling method with no function tools and
        # google_search enabled — Gemini will ground its reply on web results.
        from google.genai import types as genai_types

        contents = [
            genai_types.Content(role="user", parts=[genai_types.Part(text=args.query)])
        ]
        try:
            resp = await ctx.gemini.generate_with_tools(
                contents=contents,
                tools=[],
                enable_google_search=True,
            )
        except Exception as exc:  # noqa: BLE001 — surface as bounded tool error
            return {"error": f"web_search failed: {exc}"}

        return {
            "answer": resp.text or "",
            "citations": resp.citations,
        }
