"""Agent and tool-use metrics over ``tool_calls`` versus ``expected_tool_calls``.

These compare what an agent did with what it should have done: which tools, in which order, with which arguments.
Tool calls come from the sample, or from the TOOL spans of its recorded trace. For trace-level behaviour (loops,
forbidden steps, budgets, safety boundaries, planning, multi-agent hand-offs) use the Ananke evaluators, which are
registered as ``ananke.*`` metrics.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from guage_kit.core.sample import Sample, ToolCall
from guage_kit.metrics import _text as T
from guage_kit.metrics.registry import metric

_F = "agent"
_REQ = ("expected_tool_calls",)
_ANY = ("tool_calls", "trace")


def _calls(sample: Sample) -> list[ToolCall]:
    from guage_kit.harness.convert import tool_calls_from_trace

    return tool_calls_from_trace(sample)


def _norm(v: Any) -> Any:
    if isinstance(v, str):
        return " ".join(v.strip().lower().split())
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, dict):
        return {k: _norm(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_norm(x) for x in v]
    return v


def _args_score(actual: dict[str, Any], expected: dict[str, Any]) -> float:
    if not expected:
        return 1.0
    hits = sum(1 for k, v in expected.items() if k in actual and _norm(actual[k]) == _norm(v))
    return hits / len(expected)


@metric("tool_call_f1", family=_F, requires=_REQ, requires_any=_ANY)
def tool_call_f1(sample: Sample) -> tuple[float, dict[str, Any]]:
    """F1 over tool names (as multisets): right tools called, no extra ones, none missing."""
    got = Counter(c.name for c in _calls(sample))
    want = Counter(c.name for c in sample.expected_tool_calls)
    common = sum((got & want).values())
    p = common / sum(got.values()) if got else 0.0
    r = common / sum(want.values()) if want else 0.0
    return T.f1(p, r), {
        "precision": round(p, 4),
        "recall": round(r, 4),
        "missing": sorted((want - got).elements()),
        "unexpected": sorted((got - want).elements()),
    }


@metric("tool_args_accuracy", family=_F, requires=_REQ, requires_any=_ANY)
def tool_args_accuracy(sample: Sample) -> tuple[float, dict[str, Any]]:
    """For each expected call, the share of its arguments the best-matching actual call got right (0 if not called)."""
    calls = _calls(sample)
    used: set[int] = set()
    per: list[dict[str, Any]] = []
    for exp in sample.expected_tool_calls:
        best, best_i = 0.0, -1
        for i, c in enumerate(calls):
            if i in used or c.name != exp.name:
                continue
            s = _args_score(c.arguments, exp.arguments)
            if s > best or best_i == -1:
                best, best_i = s, i
        if best_i >= 0:
            used.add(best_i)
        per.append(
            {
                "tool": exp.name,
                "score": round(best if best_i >= 0 else 0.0, 4),
                "called": best_i >= 0,
            }
        )
    value = sum(float(p["score"]) for p in per) / len(per) if per else 1.0
    return value, {"calls": per}


@metric("tool_sequence_match", family=_F, requires=_REQ, requires_any=_ANY)
def tool_sequence_match(sample: Sample) -> tuple[float, dict[str, Any]]:
    """Order-aware similarity of the tool sequence: LCS length ÷ the longer sequence (1 is the same order)."""
    got = [c.name for c in _calls(sample)]
    want = [c.name for c in sample.expected_tool_calls]
    longest = max(len(got), len(want))
    value = T.lcs_length(got, want) / longest if longest else 1.0
    return value, {"actual": got, "expected": want}


@metric("tool_calls_exact", family=_F, requires=_REQ, requires_any=_ANY)
def tool_calls_exact(sample: Sample) -> float:
    """1 when the agent made exactly the expected calls, in order, with the expected arguments."""
    got = _calls(sample)
    want = sample.expected_tool_calls
    return float(
        len(got) == len(want)
        and all(
            g.name == w.name and _args_score(g.arguments, w.arguments) == 1.0
            for g, w in zip(got, want, strict=True)
        )
    )


@metric("tool_error_rate", family=_F, requires_any=_ANY, higher_is_better=False)
def tool_error_rate(sample: Sample) -> float | None:
    """Share of the agent's tool calls that returned an error."""
    calls = _calls(sample)
    if not calls:
        return None
    return sum(1 for c in calls if c.error) / len(calls)


@metric("redundant_tool_calls", family=_F, requires_any=_ANY, higher_is_better=False)
def redundant_tool_calls(sample: Sample) -> tuple[float, dict[str, Any]] | None:
    """Share of calls that repeat an earlier call with the same tool and arguments."""
    calls = _calls(sample)
    if not calls:
        return None
    seen: set[str] = set()
    dup = []
    import json

    for c in calls:
        key = c.name + json.dumps(c.arguments, sort_keys=True, default=str)
        if key in seen:
            dup.append(c.name)
        seen.add(key)
    return len(dup) / len(calls), {"repeated": dup}


@metric("goal_success", family=_F, requires=())
def goal_success(sample: Sample) -> float | None:
    """1 when the task succeeded, from ``metadata.success`` (set by your harness or environment check)."""
    v = sample.metadata.get("success")
    if v is None:
        return None
    return float(bool(v))
