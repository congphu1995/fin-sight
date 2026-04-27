from typing import ClassVar

from pydantic import BaseModel, Field


class GenericExtraction(BaseModel):
    __extraction_key__: ClassVar[str] = "generic"
    __version__: ClassVar[str] = "v1"

    summary: str
    key_findings: list[str] = Field(default_factory=list, max_length=10)
