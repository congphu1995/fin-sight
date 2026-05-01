"""Unit tests for the helpers used by GeminiClient.generate_with_tools.

We don't make real Gemini calls in unit tests — those are exercised end-to-end
in integration tests with FakeGeminiClient. Here we cover the pure helpers.
"""

from app.core.llm.gemini import _strip_additional_properties


def test_strip_top_level() -> None:
    schema = {"type": "object", "properties": {}, "additionalProperties": False}
    assert _strip_additional_properties(schema) == {"type": "object", "properties": {}}


def test_strip_nested_in_properties() -> None:
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "object",
                "properties": {"a": {"type": "string"}},
                "additionalProperties": True,
            }
        },
    }
    out = _strip_additional_properties(schema)
    assert out["properties"]["items"] == {
        "type": "object",
        "properties": {"a": {"type": "string"}},
    }


def test_strip_inside_array_items() -> None:
    schema = {
        "type": "array",
        "items": {"type": "object", "additionalProperties": False, "properties": {}},
    }
    out = _strip_additional_properties(schema)
    assert "additionalProperties" not in out["items"]


def test_strip_preserves_unrelated_keys() -> None:
    schema = {"type": "string", "format": "date", "description": "x"}
    assert _strip_additional_properties(schema) == schema
