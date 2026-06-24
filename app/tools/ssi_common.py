"""Shared helpers for the SSI tools."""

from datetime import date

NOT_CONFIGURED_DATA = {"error": "SSI market data is not configured on this server."}
NOT_CONFIGURED_TRADING = {"error": "SSI account access is not configured on this server."}


def fmt_date(d: date) -> str:
    """SSI FastConnect APIs expect dd/mm/yyyy."""
    return d.strftime("%d/%m/%Y")


def envelope(resp: object) -> dict:
    """Normalize an SSI JSON response to {status, message, data}, case-insensitively."""
    if not isinstance(resp, dict):
        return {"status": None, "message": None, "data": resp}
    lower = {str(k).lower(): v for k, v in resp.items()}
    return {
        "status": lower.get("status"),
        "message": lower.get("message"),
        "data": lower.get("data"),
    }
