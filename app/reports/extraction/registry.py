"""Explicit registry mapping extraction keys to (schema, prompt, version) bundles.

Static imports — pyright/mypy verify the registry at type-check time. To add a new
extraction key:

    1. Create a folder `extraction/<name>/` with `schema.py` (Pydantic class with
       `__extraction_key__` and `__version__`) and `prompt.md`.
    2. Add one import + one dict entry below.
    3. Point `report_types.code = '<key>'` in the DB (and add a row in the
       crawler's TYPE_FILTER mapping if the source needs a per-type API value).

The folder name SHOULD match `__extraction_key__` for navigability — enforced by
`tests/unit/reports/test_extraction_registry.py`.
"""

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from app.reports.extraction.company.schema import CompanyExtraction
from app.reports.extraction.generic.schema import GenericExtraction
from app.reports.extraction.industry.schema import IndustryExtraction
from app.reports.extraction.macro.schema import MacroExtraction
from app.reports.extraction.technical.schema import TechnicalExtraction
from app.reports.extraction.thematic.schema import ThematicExtraction


@dataclass(frozen=True)
class ExtractionDef:
    key: str
    schema: type[BaseModel]
    prompt_template: str
    prompt_version: str


_HERE = Path(__file__).parent


def _build(folder: str, schema_cls: type[BaseModel]) -> ExtractionDef:
    return ExtractionDef(
        key=schema_cls.__extraction_key__,
        schema=schema_cls,
        prompt_template=(_HERE / folder / "prompt.md").read_text(encoding="utf-8"),
        prompt_version=schema_cls.__version__,
    )


EXTRACTION_REGISTRY: dict[str, ExtractionDef] = {
    "company": _build("company", CompanyExtraction),
    "industry": _build("industry", IndustryExtraction),
    "macro": _build("macro", MacroExtraction),
    "technical": _build("technical", TechnicalExtraction),
    "thematic": _build("thematic", ThematicExtraction),
    "generic": _build("generic", GenericExtraction),
}
