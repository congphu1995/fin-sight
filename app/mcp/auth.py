"""Static bearer-token auth for the MCP sub-app.

Mira authenticates with `Authorization: Bearer <MCP_AUTH_TOKEN>`. This guards
only the mounted MCP routes (not /healthz). On a private tailnet an empty token
disables the check (the middleware isn't added).
"""

from __future__ import annotations

import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, token: str) -> None:
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        header = request.headers.get("authorization", "")
        prefix = "Bearer "
        presented = header[len(prefix) :] if header.startswith(prefix) else ""
        if not (presented and hmac.compare_digest(presented, self._token)):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)
