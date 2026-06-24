"""Render tool result dicts into concise text for the model.

Hard rule (Mira's Gemini "empty-final" trigger): the returned text must NEVER
end on a line of opaque tokens (ids/hashes). Ids go INLINE mid-line; every
renderer ends on a prose/summary line. Keep results compact.
"""

from __future__ import annotations

from typing import Any

_MAX_SUMMARY = 400
_MAX_ROWS = 50


def _truncate(s: str | None, n: int = _MAX_SUMMARY) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[:n].rstrip() + "…"


def _err(msg: str) -> str:
    return f"Error: {msg}"


def _row_line(row: Any) -> str:
    if isinstance(row, dict):
        return "- " + ", ".join(f"{k}={v}" for k, v in row.items())
    return f"- {row}"


# --- Tier 1: stored reports ---


def render_stock_analysis(p: dict) -> str:
    if "error" in p:
        return _err(p["error"])
    ticker = p.get("ticker", "?")
    reports = p.get("reports", [])
    if not reports:
        return f"No extracted analyst reports found for {ticker}."
    lines = [f"Analyst view for {ticker} — {len(reports)} recent report(s), newest first:"]
    for r in reports:
        bits = []
        if r.get("recommendation"):
            bits.append(str(r["recommendation"]))
        if r.get("target_price") is not None:
            tp = f"TP {r['target_price']:g} {r.get('target_currency') or ''}".strip()
            bits.append(tp)
        if r.get("outlook"):
            bits.append(str(r["outlook"]))
        head = " · ".join(bits) if bits else "no rating"
        date = r.get("published_at") or "n/a"
        line = (
            f"- [{r.get('report_type_code')}] {r.get('title')} "
            f"({date}, id {r.get('report_id')}): {head}"
        )
        if r.get("summary"):
            line += f" — {_truncate(r['summary'])}"
        lines.append(line)
    return "\n".join(lines)


def render_search_reports(p: dict) -> str:
    if "error" in p:
        return _err(p["error"])
    reports = p.get("reports", [])
    if not reports:
        return "No reports matched those filters."
    lines = [f"{p.get('count', len(reports))} report(s), newest first:"]
    for r in reports:
        date = r.get("published_at") or "n/a"
        flag = "extracted" if r.get("has_extraction") else "not extracted"
        ticker = r.get("ticker") or "—"
        lines.append(
            f"- [{r.get('report_type_code')}] {ticker} · {r.get('title')} "
            f"({date}, {r.get('publisher') or 'n/a'}, id {r.get('report_id')}) — {flag}"
        )
    return "\n".join(lines)


def render_report_metrics(p: dict) -> str:
    if "error" in p:
        return _err(p["error"])
    parts = [
        f"Report {p.get('report_id')} — extracted {p.get('extracted_at', 'n/a')} "
        f"by {p.get('model', 'n/a')}:"
    ]
    if p.get("recommendation"):
        parts.append(f"Recommendation: {p['recommendation']}.")
    if p.get("target_price") is not None:
        parts.append(
            f"Target price: {p['target_price']:g} {p.get('target_currency') or ''}".strip() + "."
        )
    if p.get("horizon"):
        parts.append(f"Horizon: {p['horizon']}.")
    extras = p.get("extras")
    if isinstance(extras, dict) and extras:
        parts.append("Extra fields: " + ", ".join(sorted(extras)) + ".")
    # Summary last so the text ends on prose.
    if p.get("summary"):
        parts.append(f"Summary: {_truncate(p['summary'], 1200)}")
    else:
        parts.append("(No summary in this extraction.)")
    return "\n".join(parts)


def render_facets(p: dict) -> str:
    if "error" in p:
        return _err(p["error"])
    vals = p.get("values", [])
    if not vals:
        return f"No values found for facet '{p.get('facet')}'."
    inline = ", ".join(f"{v.get('value')} ({v.get('count')})" for v in vals)
    return f"Facet '{p.get('facet')}' — {len(vals)} value(s): {inline}."


def render_ask_pdf(p: dict) -> str:
    if "error" in p:
        return _err(p["error"])
    head = " ".join(x for x in (p.get("ticker"), p.get("title")) if x)
    return f"{head} (id {p.get('report_id')}) — {p.get('answer', '').strip()}".strip()


# --- Tier 2: live SSI ---


def _render_rows(label: str, env: dict) -> str:
    data = env.get("data")
    if not data:
        return (
            f"SSI returned no data for {label} (status {env.get('status')}: {env.get('message')})."
        )
    rows = data if isinstance(data, list) else [data]
    lines = [f"SSI {label}:"]
    for row in rows[:_MAX_ROWS]:
        lines.append(_row_line(row))
    if len(rows) > _MAX_ROWS:
        lines.append(f"... (+{len(rows) - _MAX_ROWS} more rows)")
    lines.append(f"({len(rows)} row(s) for {label}.)")
    return "\n".join(lines)


def render_ssi_market(p: dict) -> str:
    if "error" in p:
        return _err(p["error"])
    label = p.get("symbol") or p.get("market") or p.get("index") or "market data"
    return _render_rows(str(label), p)


def render_ssi_account(p: dict) -> str:
    if "error" in p:
        return _err(p["error"])
    # Combined derivatives shape: {account, positions: env, balance: env}
    if "positions" in p and "balance" in p:
        pos = _render_rows("your derivatives positions", p["positions"])
        bal = _render_rows("your derivatives balance", p["balance"])
        return f"{pos}\n{bal}"
    return _render_rows("your account", p)
