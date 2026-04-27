from typing import ClassVar, Literal

from pydantic import BaseModel, Field

Outlook = Literal["POSITIVE", "NEUTRAL", "NEGATIVE"]
Direction = Literal["UP", "DOWN", "FLAT"]


class MacroIndicator(BaseModel):
    value: float | None = None
    unit: str | None = None
    direction: Direction | None = None
    commentary: str | None = None


class MacroExtraction(BaseModel):
    __extraction_key__: ClassVar[str] = "macro"
    __version__: ClassVar[str] = "v1"

    summary: str
    period: str = Field(..., description="Period the report covers, e.g. 'Q1 2026', 'April 2026'")
    market_outlook: Outlook | None = None
    gdp_outlook: MacroIndicator | None = None
    inflation_outlook: MacroIndicator | None = None
    interest_rate_outlook: MacroIndicator | None = None
    fx_outlook: MacroIndicator | None = None
    key_themes: list[str] = Field(default_factory=list, max_length=5)
    recommended_sectors: list[str] = Field(default_factory=list)
