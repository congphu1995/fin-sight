from decimal import Decimal
from typing import ClassVar, Literal

from pydantic import BaseModel, Field

Recommendation = Literal[
    "BUY",
    "HOLD",
    "SELL",
    "ACCUMULATE",
    "REDUCE",
    "OUTPERFORM",
    "UNDERPERFORM",
    "NEUTRAL",
]
Currency = Literal["VND", "USD"]
Horizon = Literal["3M", "6M", "12M", "18M", "24M"]


class NamedMetric(BaseModel):
    """A name/value pair. Used in place of `dict[str, float]` because Gemini's
    structured-output mode rejects JSON Schema `additionalProperties`."""

    name: str
    value: float


class CompanyExtraction(BaseModel):
    __extraction_key__: ClassVar[str] = "company"
    __version__: ClassVar[str] = "v1"

    summary: str = Field(..., description="200-500 word abstract of the report's thesis")
    recommendation: Recommendation | None = None
    target_price: Decimal | None = None
    target_currency: Currency | None = "VND"
    current_price: Decimal | None = None
    time_horizon: Horizon | None = "12M"
    analyst: list[str] = Field(default_factory=list)
    key_drivers: list[str] = Field(default_factory=list, max_length=5)
    key_risks: list[str] = Field(default_factory=list, max_length=5)
    financial_highlights: list[NamedMetric] = Field(default_factory=list)
