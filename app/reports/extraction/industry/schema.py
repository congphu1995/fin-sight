from decimal import Decimal
from typing import ClassVar, Literal

from pydantic import BaseModel, Field

Outlook = Literal["POSITIVE", "NEUTRAL", "NEGATIVE"]


class TopPick(BaseModel):
    ticker: str
    recommendation: str | None = None
    target_price: Decimal | None = None
    rationale: str | None = None


class NamedMetric(BaseModel):
    """`dict[str, float]` would generate `additionalProperties` which Gemini rejects."""

    name: str
    value: float


class IndustryExtraction(BaseModel):
    __extraction_key__: ClassVar[str] = "industry"
    __version__: ClassVar[str] = "v2"

    summary: str
    industry: str = Field(
        ...,
        description=(
            "Canonical English sector label from the prompt's allowed list "
            "(Steel, Banking, Real Estate, ...). Use 'Other' only when none fit."
        ),
    )
    outlook: Outlook | None = None
    top_picks: list[TopPick] = Field(default_factory=list)
    key_drivers: list[str] = Field(default_factory=list, max_length=5)
    key_risks: list[str] = Field(default_factory=list, max_length=5)
    key_metrics: list[NamedMetric] = Field(default_factory=list)
