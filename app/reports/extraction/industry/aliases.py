"""Canonical-vocabulary mapping for the `industry_name` facet.

The v2 industry prompt (see prompt.md) instructs Gemini to return one of a
fixed set of English labels. The LLM is mostly compliant but occasionally
returns the Vietnamese form as written ("Tôn mạ") or a near-miss ("Banks"
instead of "Banking"). This module is the runtime backstop: it normalizes
those into the canonical label before the value lands in the typed column.

The canonical list MUST stay in sync with the bullet list in
`app/reports/extraction/industry/prompt.md`. When you add a sector there,
add its English form (lowercased) and any Vietnamese aliases here.
"""

from __future__ import annotations

# Lookup is case-insensitive and trim-insensitive (see canonicalize_industry).
# Keys are pre-lowercased / pre-stripped. Values are the canonical English form.
CANONICAL_INDUSTRIES: dict[str, str] = {
    # Steel
    "steel": "Steel",
    "thép": "Steel",
    "tôn mạ": "Steel",
    "sắt thép": "Steel",
    "thép và tôn mạ": "Steel",
    # Banking
    "banking": "Banking",
    "banks": "Banking",
    "bank": "Banking",
    "ngân hàng": "Banking",
    # Real Estate
    "real estate": "Real Estate",
    "bất động sản": "Real Estate",
    "bđs": "Real Estate",
    "bđs dân dụng": "Real Estate",
    # Industrial Real Estate
    "industrial real estate": "Industrial Real Estate",
    "bđs khu công nghiệp": "Industrial Real Estate",
    "kcn": "Industrial Real Estate",
    # Oil & Gas
    "oil & gas": "Oil & Gas",
    "oil and gas": "Oil & Gas",
    "dầu khí": "Oil & Gas",
    "năng lượng dầu khí": "Oil & Gas",
    # Power & Utilities
    "power & utilities": "Power & Utilities",
    "power and utilities": "Power & Utilities",
    "utilities": "Power & Utilities",
    "điện": "Power & Utilities",
    "ngành điện": "Power & Utilities",
    "năng lượng điện": "Power & Utilities",
    "tiện ích": "Power & Utilities",
    # Chemicals & Fertilizers
    "chemicals & fertilizers": "Chemicals & Fertilizers",
    "chemicals and fertilizers": "Chemicals & Fertilizers",
    "chemicals": "Chemicals & Fertilizers",
    "fertilizers": "Chemicals & Fertilizers",
    "hóa chất": "Chemicals & Fertilizers",
    "phân bón": "Chemicals & Fertilizers",
    "hóa chất cơ bản": "Chemicals & Fertilizers",
    # Textiles & Apparel
    "textiles & apparel": "Textiles & Apparel",
    "textiles and apparel": "Textiles & Apparel",
    "textiles": "Textiles & Apparel",
    "apparel": "Textiles & Apparel",
    "dệt may": "Textiles & Apparel",
    "may mặc": "Textiles & Apparel",
    # Retail & Consumer
    "retail & consumer": "Retail & Consumer",
    "retail and consumer": "Retail & Consumer",
    "retail": "Retail & Consumer",
    "consumer": "Retail & Consumer",
    "bán lẻ": "Retail & Consumer",
    "tiêu dùng": "Retail & Consumer",
    "hàng tiêu dùng": "Retail & Consumer",
    # Food & Beverage
    "food & beverage": "Food & Beverage",
    "food and beverage": "Food & Beverage",
    "f&b": "Food & Beverage",
    "thực phẩm": "Food & Beverage",
    "đồ uống": "Food & Beverage",
    # IT & Telecom
    "it & telecom": "IT & Telecom",
    "it and telecom": "IT & Telecom",
    "it": "IT & Telecom",
    "telecom": "IT & Telecom",
    "công nghệ": "IT & Telecom",
    "viễn thông": "IT & Telecom",
    "cntt": "IT & Telecom",
    # Logistics & Shipping
    "logistics & shipping": "Logistics & Shipping",
    "logistics and shipping": "Logistics & Shipping",
    "logistics": "Logistics & Shipping",
    "shipping": "Logistics & Shipping",
    "vận tải": "Logistics & Shipping",
    "cảng biển": "Logistics & Shipping",
    # Aviation
    "aviation": "Aviation",
    "hàng không": "Aviation",
    # Construction & Materials
    "construction & materials": "Construction & Materials",
    "construction and materials": "Construction & Materials",
    "construction": "Construction & Materials",
    "materials": "Construction & Materials",
    "xây dựng": "Construction & Materials",
    "vật liệu xây dựng": "Construction & Materials",
    "vlxd": "Construction & Materials",
    # Insurance
    "insurance": "Insurance",
    "bảo hiểm": "Insurance",
    # Securities
    "securities": "Securities",
    "chứng khoán": "Securities",
    "công ty chứng khoán": "Securities",
    # Healthcare & Pharma
    "healthcare & pharma": "Healthcare & Pharma",
    "healthcare and pharma": "Healthcare & Pharma",
    "healthcare": "Healthcare & Pharma",
    "pharma": "Healthcare & Pharma",
    "pharmaceutical": "Healthcare & Pharma",
    "y tế": "Healthcare & Pharma",
    "dược": "Healthcare & Pharma",
    "dược phẩm": "Healthcare & Pharma",
    # Automotive
    "automotive": "Automotive",
    "auto": "Automotive",
    "ô tô": "Automotive",
    "xe điện": "Automotive",
    # Other (catch-all)
    "other": "Other",
}


def canonicalize_industry(value: str | None) -> str | None:
    """Map an arbitrary industry string to its canonical English label.

    Unknown values pass through unchanged (after trim) — the canonical list
    isn't exhaustive of every sector that might appear, so we'd rather record
    a novel value than coerce it to "Other".
    """
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return CANONICAL_INDUSTRIES.get(cleaned.lower(), cleaned)
