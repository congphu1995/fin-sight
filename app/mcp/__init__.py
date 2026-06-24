"""MCP server — exposes the read-only tools to Mira over streamable-HTTP.

`build_mcp_server(settings)` returns a FastMCP whose tools wrap `app/tools`'s
registry. main.py mounts `mcp.streamable_http_app()` at settings.mcp_path and
runs `mcp.session_manager` in the lifespan.
"""

from app.mcp.server import build_mcp_server

__all__ = ["build_mcp_server"]
