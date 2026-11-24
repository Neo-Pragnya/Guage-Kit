"""Structured-output metrics: valid JSON or YAML, JSON Schema conformance, field-level accuracy, code that parses.

JSON is found in fenced blocks (```json … ```) or as the first balanced object/array in the text. The built-in
schema validator covers the keywords models are usually asked to follow (type, properties, required,
additionalProperties, items, enum, const, minimum/maximum, minLength/maxLength, pattern, minItems/maxItems,
anyOf/oneOf/allOf). Install ``guage-kit[jsonschema]`` for the full specification.
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

import yaml

from guage_kit.core.sample import Sample
from guage_kit.metrics.registry import metric

_F = "structured"
_FENCE = re.compile(r"```(?:json|JSON)?\s*\n(.*?)```", re.DOTALL)
_CODE_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)


def extract_json(text: str) -> tuple[bool, Any]:
    """Return (found, value). Tries the whole text, fenced blocks, then the first balanced {...} or [...]."""
    text = text.strip()
    candidates = [text, *_FENCE.findall(text)]
    for c in candidates:
        try:
            return True, json.loads(c)
        except (json.JSONDecodeError, ValueError):
            continue
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        while start != -1:
            depth = 0
            in_str = False
            esc = False
            for i in range(start, len(text)):
                ch = text[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                elif ch == '"':
                    in_str = True
                elif ch == opener:
                    depth += 1
                elif ch == closer:
                    depth -= 1
                    if depth == 0:
                        try:
                            return True, json.loads(text[start : i + 1])
                        except json.JSONDecodeError:
                            break
            start = text.find(opener, start + 1)
    return False, None


def _output_json(sample: Sample) -> tuple[bool, Any]:
    if isinstance(sample.output, (dict, list)):
        return True, sample.output
    return extract_json(sample.output_text)


@metric("json_valid", family=_F, requires=("output",))
def json_valid(sample: Sample, *, strict: bool = False) -> float:
    """1 when the output is (``strict``) or contains (default) valid JSON."""
    if strict:
        try:
            json.loads(sample.output_text)
            return 1.0
        except json.JSONDecodeError:
            return 0.0
    return float(_output_json(sample)[0])


@metric("yaml_valid", family=_F, requires=("output",))
def yaml_valid(sample: Sample) -> float:
    """1 when the output parses as YAML into a mapping or list."""
    try:
        return float(isinstance(yaml.safe_load(sample.output_text), (dict, list)))
    except yaml.YAMLError:
        return 0.0


_TYPES: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "array": (list,),
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "null": (type(None),),
}


def validate_schema(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Errors (empty when valid) for the common JSON Schema subset."""
    try:
        import jsonschema

        validator = jsonschema.Draft202012Validator(schema)
        return [
            f"{'/'.join(str(p) for p in e.absolute_path) or '$'}: {e.message}"
            for e in validator.iter_errors(value)
        ]
    except ImportError:
        return _validate(value, schema, path)


def _validate(value: Any, schema: dict[str, Any], path: str) -> list[str]:
    errs: list[str] = []
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        ok = False
        for name in types:
            py = _TYPES.get(name, ())
            if isinstance(value, bool) and name in ("integer", "number"):
                continue
            if isinstance(value, py):
                ok = True
        if not ok:
            return [f"{path}: expected {t}, got {type(value).__name__}"]
    if "const" in schema and value != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errs.append(f"{path}: {value} > maximum {schema['maximum']}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errs.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                errs.append(f"{path}: missing required property {req!r}")
        for k, v in value.items():
            if k in props:
                errs.extend(_validate(v, props[k], f"{path}.{k}"))
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected property {k!r}")
            elif isinstance(schema.get("additionalProperties"), dict):
                errs.extend(_validate(v, schema["additionalProperties"], f"{path}.{k}"))
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append(f"{path}: more than {schema['maxItems']} items")
        if isinstance(schema.get("items"), dict):
            for i, item in enumerate(value):
                errs.extend(_validate(item, schema["items"], f"{path}[{i}]"))
    for sub in schema.get("allOf", []):
        errs.extend(_validate(value, sub, path))
    if "anyOf" in schema and all(_validate(value, s, path) for s in schema["anyOf"]):
        errs.append(f"{path}: matches none of anyOf")
    if "oneOf" in schema and sum(1 for s in schema["oneOf"] if not _validate(value, s, path)) != 1:
        errs.append(f"{path}: must match exactly one of oneOf")
    return errs


@metric("json_schema", family=_F, requires=("output",))
def json_schema(
    sample: Sample, *, schema: dict[str, Any] | None = None
) -> tuple[float, dict[str, Any]] | None:
    """1 when the output's JSON conforms to the schema (parameter, or ``metadata.schema``)."""
    sch = schema or sample.metadata.get("schema")
    if not isinstance(sch, dict):
        return None
    found, value = _output_json(sample)
    if not found:
        return 0.0, {"errors": ["no JSON found"], "reason": "no JSON found"}
    errors = validate_schema(value, sch)
    return float(not errors), {"errors": errors[:20], **({"reason": errors[0]} if errors else {})}


def _leaves(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            out.update(_leaves(v, f"{prefix}.{k}" if prefix else str(k)))
        return out or {prefix: {}}
    if isinstance(value, list) and value and all(isinstance(v, (dict, list)) for v in value):
        out = {}
        for i, v in enumerate(value):
            out.update(_leaves(v, f"{prefix}[{i}]"))
        return out
    return {prefix: value}


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, str) and isinstance(b, str):
        return a.strip().lower() == b.strip().lower()
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(float(a) - float(b)) <= 1e-9 * max(1.0, abs(float(b)))
    if isinstance(a, list) and isinstance(b, list):
        return sorted(map(str, a)) == sorted(map(str, b))
    return bool(a == b)


def _expected_json(sample: Sample) -> Any:
    if isinstance(sample.expected, (dict, list)):
        return sample.expected
    found, value = (
        extract_json(sample.expected_texts[0]) if sample.expected_texts else (False, None)
    )
    return value if found else None


@metric("json_field_accuracy", family=_F, requires=("output", "expected"))
def json_field_accuracy(sample: Sample) -> tuple[float, dict[str, Any]] | None:
    """F1 over leaf fields: a field counts when the path exists in both and the values match (extraction tasks)."""
    want = _expected_json(sample)
    if want is None:
        return None
    found, got = _output_json(sample)
    if not found:
        return 0.0, {"reason": "no JSON found"}
    w, g = _leaves(want), _leaves(got)
    correct = [k for k in w if k in g and _same(g[k], w[k])]
    p = len(correct) / len(g) if g else 0.0
    r = len(correct) / len(w) if w else 0.0
    f = 0.0 if p + r == 0 else 2 * p * r / (p + r)
    wrong = {k: {"expected": w[k], "got": g.get(k)} for k in w if k not in correct}
    return f, {
        "precision": round(p, 4),
        "recall": round(r, 4),
        "mismatches": dict(list(wrong.items())[:20]),
    }


@metric("json_match", family=_F, requires=("output", "expected"))
def json_match(sample: Sample) -> float | None:
    """1 when the output JSON equals the expected JSON (key order ignored)."""
    want = _expected_json(sample)
    if want is None:
        return None
    found, got = _output_json(sample)
    return float(found and got == want)


@metric("python_syntax", family=_F, requires=("output",))
def python_syntax(sample: Sample) -> tuple[float, dict[str, str]]:
    """1 when the output (or its first ```python block) parses as Python. Nothing is executed."""
    blocks = _CODE_FENCE.findall(sample.output_text)
    code = blocks[0] if blocks else sample.output_text
    try:
        ast.parse(code)
        return 1.0, {}
    except SyntaxError as exc:
        return 0.0, {"reason": f"line {exc.lineno}: {exc.msg}"}
