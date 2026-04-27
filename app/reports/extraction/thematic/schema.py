from typing import ClassVar, Literal

from pydantic import BaseModel, Field

Impact = Literal["POSITIVE", "NEUTRAL", "NEGATIVE"]


class TickerImpact(BaseModel):
    ticker: str
    impact: Impact
    rationale: str | None = None


class ThematicExtraction(BaseModel):
    __extraction_key__: ClassVar[str] = "thematic"
    __version__: ClassVar[str] = "v1"

    summary: str
    topic: str
    key_findings: list[str] = Field(default_factory=list, max_length=8)
    affected_tickers: list[TickerImpact] = Field(default_factory=list)
    policy_references: list[str] = Field(default_factory=list)
