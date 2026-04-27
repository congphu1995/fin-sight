from decimal import Decimal
from typing import ClassVar, Literal

from pydantic import BaseModel, Field

IndexDirection = Literal["BULLISH", "BEARISH", "SIDEWAYS"]


class IndexOutlook(BaseModel):
    symbol: str
    direction: IndexDirection | None = None
    support: list[float] = Field(default_factory=list)
    resistance: list[float] = Field(default_factory=list)
    commentary: str | None = None


class TechnicalSignal(BaseModel):
    ticker: str
    signal: str
    entry_price: Decimal | None = None
    stop_loss: Decimal | None = None
    target: Decimal | None = None


class TechnicalExtraction(BaseModel):
    __extraction_key__: ClassVar[str] = "technical"
    __version__: ClassVar[str] = "v1"

    summary: str
    period: str
    index_outlook: list[IndexOutlook] = Field(default_factory=list)
    top_signals: list[TechnicalSignal] = Field(default_factory=list)
    commentary: str | None = None
