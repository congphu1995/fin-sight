import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from app.agent.tools.base import Tool, ToolContext, register

_MAX_TEXT_CHARS = 8000
_TIMEOUT_S = 10.0


class FetchUrlArgs(BaseModel):
    url: str = Field(..., min_length=1, max_length=2000)


@register
class FetchUrl(Tool):
    name = "fetch_url"
    description = (
        "Fetch the main text content of a URL. Returns plain text (HTML stripped), "
        f"truncated to {_MAX_TEXT_CHARS} characters. Use after `web_search` if "
        "you need more detail from a specific page."
    )
    args_schema = FetchUrlArgs

    async def run(self, args: FetchUrlArgs, ctx: ToolContext) -> dict:
        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT_S, follow_redirects=True
            ) as client:
                resp = await client.get(args.url)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            return {"error": f"fetch failed: {exc}"}

        content_type = resp.headers.get("content-type", "")
        if "html" not in content_type:
            text = resp.text
        else:
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)

        truncated = len(text) > _MAX_TEXT_CHARS
        return {
            "url": str(resp.url),
            "status": resp.status_code,
            "text": text[:_MAX_TEXT_CHARS],
            "truncated": truncated,
            "content_type": content_type,
        }
