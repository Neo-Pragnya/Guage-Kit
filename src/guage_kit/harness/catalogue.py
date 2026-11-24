"""Ananke's agent evaluators as Guage Kit metrics.

Ananke Plexus ships evaluators across nine agent-quality dimensions (outcome, trajectory, tool use, planning,
retrieval, safety, resilience, efficiency, multi-agent, architecture). This catalogue discovers them in the
installed harness, so a newer Ananke brings new evaluators without a Guage Kit release, and registers each as a
metric named by its Ananke id (``ananke.trajectory.loop_detection``).

Constructor arguments (an evaluator's configuration) are resolved in this order:

1. metric parameters (``params`` in code or ``guage.yaml``);
2. the sample's ``metadata.ananke`` mapping (per-sample configuration);
3. sample fields: an expected trajectory, required or allowed tools come from ``expected_tool_calls``, the optimal
   step count from its length, and any other argument from ``metadata.<argument>``.

An evaluator whose required arguments can't be resolved skips the sample and says which argument is missing.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

from guage_kit.core.results import Score
from guage_kit.core.sample import Sample
from guage_kit.errors import GuageError
from guage_kit.metrics.registry import REGISTRY, MetricInfo

REQUIRED = object()

# arguments filled from the expected tool calls when nothing else provides them
_FROM_EXPECTED_NAMES = {"expected", "required", "expected_tools", "allowed"}


@dataclass(frozen=True)
class AnankeEvaluator:
    id: str
    cls: type
    dimension: str
    deterministic: bool
    description: str
    params: dict[str, Any] = field(default_factory=dict)  # name -> default, or REQUIRED
    annotations: dict[str, str] = field(default_factory=dict)  # name -> annotation text

    @property
    def required(self) -> list[str]:
        return [k for k, v in self.params.items() if v is REQUIRED]


@cache
def discover() -> dict[str, AnankeEvaluator]:
    """Every evaluator class in the installed ``ananke.plexus.evals.evaluators`` package."""
    import ananke.plexus.evals.evaluators as pkg

    found: dict[str, AnankeEvaluator] = {}
    for mod_info in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        try:
            # module names come from walking Ananke's own installed package
            module = importlib.import_module(mod_info.name)
        except Exception:  # noqa: S112 - one broken module must not hide the rest
            continue
        for _, cls in inspect.getmembers(module, inspect.isclass):
            ev_id = getattr(cls, "id", None)
            if (
                cls.__module__ != module.__name__
                or not isinstance(ev_id, str)
                or not hasattr(cls, "evaluate")
            ):
                continue
            params: dict[str, Any] = {}
            annotations: dict[str, str] = {}
            for pname, p in inspect.signature(cls.__init__).parameters.items():
                if pname == "self" or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                    continue
                params[pname] = REQUIRED if p.default is inspect.Parameter.empty else p.default
                annotations[pname] = (
                    p.annotation
                    if isinstance(p.annotation, str)
                    else getattr(p.annotation, "__name__", str(p.annotation))
                )
            doc = (inspect.getdoc(cls) or "").split("\n\n")[0].replace("\n", " ")
            found[ev_id] = AnankeEvaluator(
                id=ev_id,
                cls=cls,
                dimension=str(getattr(cls, "dimension", "agent")),
                deterministic=bool(getattr(cls, "deterministic", True)),
                description=doc
                or f"Ananke {ev_id.split('.', 2)[-1].replace('_', ' ')} evaluator ({getattr(cls, 'dimension', '')}).",
                params=params,
                annotations=annotations,
            )
    return dict(sorted(found.items()))


def _resolve_args(
    ev: AnankeEvaluator, sample: Sample, config: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    per_sample = sample.metadata.get("ananke") or {}
    per_sample = {
        **(per_sample.get(ev.id) or {}),
        **{k: v for k, v in per_sample.items() if not isinstance(v, dict) or k in ev.params},
    }
    expected_names = [c.name for c in sample.expected_tool_calls]
    args: dict[str, Any] = {}
    missing: list[str] = []
    for name, default in ev.params.items():
        if config.get(name) is not None:
            args[name] = config[name]
        elif name in per_sample:
            args[name] = per_sample[name]
        elif name in _FROM_EXPECTED_NAMES and expected_names:
            # a single-step argument (``required: str``) is the goal action: the last expected call
            single = ev.annotations.get(name, "").strip() == "str"
            args[name] = expected_names[-1] if single else expected_names
        elif name == "optimal_steps" and expected_names:
            args[name] = len(expected_names)
        elif name in sample.metadata:
            args[name] = sample.metadata[name]
        elif default is REQUIRED:
            missing.append(name)
        else:
            args[name] = default
    return args, missing


def run_evaluator(
    ev_id: str,
    sample: Sample,
    config: dict[str, Any] | None = None,
    project_root: Path | None = None,
) -> Score:
    """Score one sample with one Ananke evaluator."""
    from ananke.plexus.evals.context import EvaluationContext

    from guage_kit.harness.convert import to_case, to_trace

    ev = discover().get(ev_id)
    if ev is None:
        raise GuageError(
            "GK-HARNESS-002",
            f"Ananke has no evaluator {ev_id!r}",
            hint="`guage metrics list --family ananke` shows them",
        )
    args, missing = _resolve_args(ev, sample, config or {})
    if missing:
        return Score(
            metric=ev_id,
            skipped=True,
            reason=f"needs {', '.join(missing)} (set params, metadata.ananke or expected_tool_calls)",
        )
    evaluator = ev.cls(**args)
    context = EvaluationContext.from_project(project_root or Path.cwd())
    results = evaluator.evaluate(case=to_case(sample), trace=to_trace(sample), context=context)
    usable = [r for r in results if r.status.value not in ("skipped",)]
    if not usable:
        reason = "; ".join(r.reason or "skipped" for r in results) or "skipped"
        return Score(metric=ev_id, skipped=True, reason=f"Ananke: {reason}")
    errors = [r for r in usable if r.status.value == "error"]
    if errors and len(errors) == len(usable):
        return Score(metric=ev_id, error=f"Ananke: {errors[0].reason}")
    values: list[float] = []
    for r in usable:
        if r.normalized_score is not None:
            values.append(float(r.normalized_score))
        else:
            values.append(1.0 if r.status.value in ("pass", "warn") else 0.0)
    value = sum(values) / len(values)
    passed = all(r.status.value in ("pass", "warn") for r in usable)
    evidence = [e for r in usable for e in r.evidence][:10]
    joined = "; ".join(r.reason for r in usable if r.reason)
    reason_text: str | None = joined or None
    return Score(
        metric=ev_id,
        value=value,
        passed=passed,
        reason=reason_text,
        details={
            "ananke": [
                {
                    "metric": r.metric,
                    "status": r.status.value,
                    "value": _plain(r.value),
                    "normalized": r.normalized_score,
                }
                for r in usable
            ],
            "evidence": evidence,
        },
    )


def _plain(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, list):
        return [_plain(x) for x in v][:20]
    return str(v)


def register_all() -> int:
    """Register every discovered Ananke evaluator in the metric registry (idempotent). Returns the count."""
    n = 0
    for ev in discover().values():
        if ev.id in REGISTRY._metrics:
            continue

        def fn(sample: Sample, *, _ev_id: str = ev.id, **config: Any) -> Score:
            return run_evaluator(_ev_id, sample, config)

        REGISTRY.add(
            MetricInfo(
                name=ev.id,
                family=f"ananke.{ev.dimension}",
                description=ev.description,
                fn=fn,
                level="sample",
                requires_any=("output", "tool_calls", "trace", "contexts"),
                deterministic=ev.deterministic,
                params={k: (None if v is REQUIRED else v) for k, v in ev.params.items()},
                reference="Ananke Plexus evaluation harness",
                source="ananke-plexus",
            )
        )
        n += 1
    return n


__all__ = ["AnankeEvaluator", "discover", "register_all", "run_evaluator"]
