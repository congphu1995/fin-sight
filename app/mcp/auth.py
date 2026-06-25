"""Static bearer-token auth for the MCP routes.

Mira authenticates with `Authorization: Bearer <MCP_AUTH_TOKEN>`. Added to the
MAIN app but scoped to `path_prefix` (the MCP mount) so /healthz stays open and
the guard runs reliably *ahead* of the mounted MCP sub-app (sub-app middleware
doesn't reliably wrap the streamable-HTTP ASGI handler). Empty token disables it
(the middleware isn't added).
"""

from __future__ import annotations

import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, token: str, path_prefix: str = "/mcp") -> None:
        super().__init__(app)
        self._token = token
        self._prefix = path_prefix

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.url.path.startswith(self._prefix):
            header = request.headers.get("authorization", "")
            presented = header[7:] if header.startswith("Bearer ") else ""
            if not (presented and hmac.compare_digest(presented, self._token)):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)
