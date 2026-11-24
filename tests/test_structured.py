"""Structured-output metrics, including the built-in schema validator used when jsonschema is absent."""

from __future__ import annotations

from typing import Any

import pytest

from guage_kit.core.sample import Sample
from guage_kit.metrics.structured import (
    _validate,
    extract_json,
    json_field_accuracy,
    json_match,
    json_schema,
    json_valid,
    python_syntax,
    yaml_valid,
)


def s(output: Any, expected: Any = None, **meta: Any) -> Sample:
    return Sample(id="1", input="x", output=output, expected=expected, metadata=meta)


def _value(r: Any) -> float | None:
    return r[0] if isinstance(r, tuple) else r


def test_extract_json_variants() -> None:
    assert extract_json('{"a": 1}') == (True, {"a": 1})
    assert extract_json('Sure:\n```json\n{"a": 2}\n```') == (True, {"a": 2})
    assert extract_json('Result: {"a": "x}\\"y", "b": [1, {"c": 2}]} done') == (
        True,
        {"a": 'x}"y', "b": [1, {"c": 2}]},
    )
    assert extract_json("items: [1, 2, 3] end") == (True, [1, 2, 3])
    assert extract_json("broken {not: json} then [4]") == (True, [4])
    assert extract_json("no json here") == (False, None)


def test_json_and_yaml_valid() -> None:
    assert json_valid(s('text {"a": 1}')) == 1.0
    assert json_valid(s('text {"a": 1}'), strict=True) == 0.0
    assert json_valid(s('{"a": 1}'), strict=True) == 1.0
    assert json_valid(s({"a": 1})) == 1.0
    assert yaml_valid(s("a: 1\nb: [2]")) == 1.0
    assert yaml_valid(s("just a sentence")) == 0.0
    assert yaml_valid(s("a: [1\n  b: }")) == 0.0


SCHEMA = {
    "type": "object",
    "required": ["name", "age", "tags"],
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string", "minLength": 2, "maxLength": 10, "pattern": "^[A-Z]"},
        "age": {"type": "integer", "minimum": 0, "maximum": 150},
        "kind": {"enum": ["a", "b"]},
        "version": {"const": 1},
        "tags": {"type": "array", "minItems": 1, "maxItems": 2, "items": {"type": "string"}},
        "score": {"type": ["number", "null"]},
    },
}


def test_builtin_validator_accepts_valid() -> None:
    ok = {"name": "Ada", "age": 36, "kind": "a", "version": 1, "tags": ["x"], "score": None}
    assert _validate(ok, SCHEMA, "$") == []


def test_builtin_validator_reports_each_rule() -> None:
    bad = {
        "name": "a" * 12,
        "age": 200,
        "kind": "z",
        "version": 2,
        "tags": ["x", "y", 3],
        "extra": 1,
    }
    errs = " | ".join(_validate(bad, SCHEMA, "$"))
    for needle in (
        "longer than",
        "does not match",
        "> maximum",
        "not in",
        "must equal",
        "more than 2 items",
        "$.tags[2]: expected string",
        "unexpected property 'extra'",
    ):
        assert needle in errs, needle
    errs = " | ".join(_validate({"name": "A", "age": -1, "tags": []}, SCHEMA, "$"))
    assert "shorter than" in errs and "< minimum" in errs and "fewer than 1 items" in errs
    assert _validate({"age": True}, {"properties": {"age": {"type": "integer"}}}, "$")
    assert "missing required property 'name'" in " ".join(_validate({}, SCHEMA, "$"))
    assert _validate("x", {"type": "object"}, "$") == ["$: expected object, got str"]


def test_builtin_validator_combinators() -> None:
    extra = {"type": "object", "additionalProperties": {"type": "integer"}}
    assert _validate({"a": 1}, extra, "$") == []
    assert _validate({"a": "x"}, extra, "$")
    assert _validate(5, {"allOf": [{"type": "integer"}, {"minimum": 10}]}, "$")
    assert _validate("x", {"anyOf": [{"type": "integer"}, {"type": "boolean"}]}, "$")
    assert _validate(3, {"anyOf": [{"type": "integer"}, {"type": "boolean"}]}, "$") == []
    one_of = {"oneOf": [{"type": "number"}, {"type": "integer"}]}
    assert _validate(3, one_of, "$")  # matches both
    assert _validate(2.5, one_of, "$") == []


def test_json_schema_metric() -> None:
    schema = {"type": "object", "required": ["a"]}
    assert json_schema(s('{"b": 1}', schema=schema)) is not None
    assert _value(json_schema(s('{"a": 1}'), schema=schema)) == 1.0
    r = json_schema(s('{"b": 1}', schema=schema))
    assert r is not None and r[0] == 0.0 and r[1]["reason"]
    r = json_schema(s("no json", schema=schema))
    assert r is not None and r[1]["reason"] == "no JSON found"
    assert json_schema(s('{"a": 1}')) is None


def test_json_field_accuracy_and_match() -> None:
    want = {"name": "Ada", "age": 36, "tags": ["b", "a"], "items": [{"x": 1}, {"x": 2}]}
    got = '{"name": " ada ", "age": 36.0, "tags": ["a", "b"], "items": [{"x": 1}, {"x": 3}]}'
    r = json_field_accuracy(s(got, want))
    assert r is not None and 0.7 < r[0] < 1.0 and "items[1].x" in r[1]["mismatches"]
    assert _value(json_field_accuracy(s("nothing", want))) == 0.0
    assert json_field_accuracy(s("{}", "not json")) is None
    r = json_field_accuracy(s('{"a": {}}', '{"a": {}}'))
    assert r is not None and r[0] == 1.0
    assert json_match(s('{"b": 2, "a": 1}', '{"a": 1, "b": 2}')) == 1.0
    assert json_match(s('{"a": 1}', {"a": 2})) == 0.0
    assert json_match(s('{"a": 1}', "plain text")) is None


@pytest.mark.parametrize(
    ("output", "ok"),
    [
        ("def f(x):\n    return x\n", 1.0),
        ("Here:\n```python\nprint('hi')\n```", 1.0),
        ("def f(:\n", 0.0),
    ],
)
def test_python_syntax(output: str, ok: float) -> None:
    score, info = python_syntax(s(output))
    assert score == ok and (ok == 1.0 or "line" in info["reason"])
