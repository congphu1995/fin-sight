"""Verify the extraction registry is consistent with the folder layout."""

from pathlib import Path

import pytest
from pydantic import BaseModel

from app.reports.extraction import EXTRACTION_REGISTRY
from app.reports.extraction.company.schema import CompanyExtraction

EXTRACTION_DIR = Path("app/reports/extraction")


def test_every_extraction_folder_is_registered() -> None:
    """A new folder under extraction/ must show up in EXTRACTION_REGISTRY."""
    folders = {
        p.name
        for p in EXTRACTION_DIR.iterdir()
        if p.is_dir()
        and not p.name.startswith("_")
        and (p / "schema.py").exists()
        and (p / "prompt.md").exists()
    }
    registry = set(EXTRACTION_REGISTRY)
    assert folders == registry, (
        f"folder tree and registry disagree:\n"
        f"  in folder, not registered: {folders - registry}\n"
        f"  registered, no folder:    {registry - folders}"
    )


def test_extraction_keys_match_folder_names() -> None:
    for key, defn in EXTRACTION_REGISTRY.items():
        assert defn.schema.__extraction_key__ == key, (
            f"key {key!r} maps to schema with __extraction_key__={defn.schema.__extraction_key__!r}"
        )


def test_every_schema_is_a_pydantic_model_with_version() -> None:
    for key, defn in EXTRACTION_REGISTRY.items():
        assert issubclass(defn.schema, BaseModel), f"{key}.schema is not a BaseModel subclass"
        assert defn.prompt_version, f"{key}.prompt_version is empty"
        assert defn.prompt_template, f"{key}.prompt_template is empty"


def test_company_schema_has_expected_fields() -> None:
    fields = set(CompanyExtraction.model_fields)
    expected = {
        "summary",
        "recommendation",
        "target_price",
        "target_currency",
        "current_price",
        "time_horizon",
        "analyst",
        "key_drivers",
        "key_risks",
        "financial_highlights",
    }
    assert expected.issubset(fields), expected - fields


def test_loading_does_not_raise() -> None:
    # Importing EXTRACTION_REGISTRY at module import time is the actual smoke test;
    # this assertion just ensures it's non-empty.
    assert len(EXTRACTION_REGISTRY) >= 6


_KEYS = ["company", "industry", "macro", "technical", "thematic", "generic"]


@pytest.mark.parametrize("key", _KEYS)
def test_required_keys_present(key: str) -> None:
    assert key in EXTRACTION_REGISTRY
