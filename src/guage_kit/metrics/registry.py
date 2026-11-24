"""The metric registry: every metric, built in or your own, is a plain function with a declaration.

Sample metrics score one sample at a time::

    @metric("starts_with_greeting", family="custom", requires=("output",))
    def starts_with_greeting(sample: Sample, *, words: tuple[str, ...] = ("hi", "hello")) -> float:
        return float(sample.output_text.lower().startswith(words))

Corpus metrics see every sample at once (BLEU, macro-F1, ECE…)::

    @corpus_metric("label_entropy", family="custom", requires=("label",))
    def label_entropy(samples: list[Sample]) -> float: ...

A function may return a float, ``(float, details)``, a :class:`~guage_kit.core.results.Score`, or ``None`` to skip
the sample. A parameter named ``ctx`` receives the :class:`MetricContext` (judge, embedder). Parameters with
defaults are configurable from code or ``guage.yaml``. ``name@k`` sets the parameter ``k`` (``recall@5``).
Third-party packages can register metrics through the ``guage_kit.metrics`` entry-point group.
"""

from __future__ import annotations

import inspect
import math
import traceback
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from importlib import metadata
from typing import Any, Literal

from guage_kit.core.results import Score
from guage_kit.core.sample import Sample
from guage_kit.errors import GuageError

Level = Literal["sample", "corpus"]


@dataclass(frozen=True)
class MetricInfo:
    name: str
    family: str
    description: str
    fn: Callable[..., Any]
    level: Level = "sample"
    requires: tuple[str, ...] = ()
    requires_any: tuple[str, ...] = ()
    higher_is_better: bool = True
    value_range: tuple[float | None, float | None] = (0.0, 1.0)
    deterministic: bool = True
    needs_judge: bool = False
    needs_embedder: bool = False
    extra: str | None = None  # the pip extra that provides an optional dependency
    params: dict[str, Any] = field(
        default_factory=dict
    )  # configurable parameters and their defaults
    preset: dict[str, Any] = field(default_factory=dict)  # fixed parameters for a named variant
    reference: str = ""  # where the metric is defined (paper, spec)
    source: str = "guage-kit"

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "family": self.family,
            "level": self.level,
            "description": self.description,
            "requires": list(self.requires),
            "requires_any": list(self.requires_any),
            "higher_is_better": self.higher_is_better,
            "range": list(self.value_range),
            "deterministic": self.deterministic,
            "needs_judge": self.needs_judge,
            "needs_embedder": self.needs_embedder,
            "extra": self.extra,
            "params": {k: _jsonable(v) for k, v in {**self.params, **self.preset}.items()},
            "reference": self.reference,
            "source": self.source,
        }


def _jsonable(v: Any) -> Any:
    if isinstance(v, tuple):
        return list(v)
    return v


@dataclass
class MetricContext:
    """What a metric may use beyond the sample: a judge, an embedder and run-wide options."""

    judge: Any = None
    embedder: Any = None
    seed: int = 0
    options: dict[str, Any] = field(default_factory=dict)


class MetricRegistry:
    """The set of known metrics: built-in families, Ananke Plexus evaluators and plugins registered through the
    ``guage_kit.metrics`` entry-point group. ``REGISTRY`` is the global instance."""

    def __init__(self) -> None:
        self._metrics: dict[str, MetricInfo] = {}
        self._plugins_loaded = False

    def add(self, info: MetricInfo, *, replace: bool = False) -> MetricInfo:
        if info.name in self._metrics and not replace:
            raise ValueError(f"metric {info.name!r} is already registered")
        self._metrics[info.name] = info
        return info

    def variant(self, name: str, base: str, description: str = "", **preset: Any) -> MetricInfo:
        """Register a named preset of another metric (``rouge1`` is ``rouge`` with ``variant='rouge1'``)."""
        b = self.get(base)
        params = {k: v for k, v in b.params.items() if k not in preset}
        info = MetricInfo(
            **{
                **b.__dict__,
                "name": name,
                "description": description or b.description,
                "params": params,
                "preset": {**b.preset, **preset},
            }
        )
        return self.add(info)

    def get(self, name: str) -> MetricInfo:
        self.load_plugins()
        if name in self._metrics:
            return self._metrics[name]
        close = _closest(name, list(self._metrics))
        raise GuageError(
            "GK-METRIC-001",
            f"unknown metric {name!r}",
            hint=f"did you mean {close!r}? `guage metrics list` shows all"
            if close
            else "`guage metrics list` shows all",
        )

    def __contains__(self, name: str) -> bool:
        self.load_plugins()
        return name in self._metrics

    def all(self) -> list[MetricInfo]:
        self.load_plugins()
        return sorted(self._metrics.values(), key=lambda m: (m.family, m.name))

    def families(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for m in self.all():
            out.setdefault(m.family, []).append(m.name)
        return out

    def load_plugins(self) -> None:
        """Import modules advertised in the ``guage_kit.metrics`` entry-point group (once)."""
        if self._plugins_loaded:
            return
        self._plugins_loaded = True
        for ep in metadata.entry_points(group="guage_kit.metrics"):
            try:
                ep.load()
            except Exception:  # a broken plugin must not break the built-ins
                traceback.print_exc()


REGISTRY = MetricRegistry()


def _signature_params(fn: Callable[..., Any], level: Level) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for i, (pname, p) in enumerate(inspect.signature(fn).parameters.items()):
        if i == 0 or pname == "ctx":
            continue  # the sample (or samples) argument, and the context
        if p.default is inspect.Parameter.empty:
            raise TypeError(f"metric parameter {pname!r} of {fn.__name__} needs a default")
        params[pname] = p.default
    return params


def _decorator(level: Level) -> Callable[..., Callable[[Callable[..., Any]], Callable[..., Any]]]:
    def outer(
        name: str,
        *,
        family: str,
        description: str = "",
        requires: Sequence[str] = (),
        requires_any: Sequence[str] = (),
        higher_is_better: bool = True,
        value_range: tuple[float | None, float | None] = (0.0, 1.0),
        deterministic: bool = True,
        needs_judge: bool = False,
        needs_embedder: bool = False,
        extra: str | None = None,
        reference: str = "",
        registry: MetricRegistry | None = None,
        replace: bool = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def inner(fn: Callable[..., Any]) -> Callable[..., Any]:
            doc = description or (inspect.getdoc(fn) or "").split("\n\n")[0].replace("\n", " ")
            info = MetricInfo(
                name=name,
                family=family,
                description=doc,
                fn=fn,
                level=level,
                requires=tuple(requires),
                requires_any=tuple(requires_any),
                higher_is_better=higher_is_better,
                value_range=value_range,
                deterministic=deterministic,
                needs_judge=needs_judge,
                needs_embedder=needs_embedder,
                extra=extra,
                params=_signature_params(fn, level),
                reference=reference,
                source=fn.__module__.split(".")[0],
            )
            (registry or REGISTRY).add(info, replace=replace)
            fn.metric_info = info  # type: ignore[attr-defined]
            return fn

        return inner

    outer.__doc__ = _DECORATOR_DOCS[level]
    return outer


_DECORATOR_DOCS: dict[str, str] = {
    "sample": """Register a function as a sample-level metric.

    The function receives one :class:`Sample` (and ``ctx`` if it declares it) and returns a float, a
    ``(value, details)`` tuple, a :class:`Score`, or None to skip the sample. Keyword-only parameters with defaults
    become the metric's configurable ``params``. ``requires`` lists sample fields that must be present (the sample
    is skipped otherwise); ``requires_any`` needs at least one of them. The first paragraph of the docstring is the
    description, unless ``description`` is given.

    Example::

        @metric("starts_polite", family="text", requires=("output",))
        def starts_polite(sample, *, words=("hello", "hi")):
            \"\"\"1 when the output opens with a greeting.\"\"\"
            return float(sample.output_text.lower().startswith(tuple(words)))
    """,
    "corpus": """Register a function as a corpus-level metric, computed over all usable samples at once.

    The function receives the list of samples that have the required fields and returns a float, a
    ``(value, details)`` tuple or a ``CorpusOutput``. Use it for statistics that are not averages of per-sample
    scores (corpus BLEU, F1, ECE, percentiles). Confidence intervals come from resampling the samples. Other
    arguments are as for :func:`metric`.
    """,
}

metric = _decorator("sample")
corpus_metric = _decorator("corpus")


# ── binding: a metric with its parameters, display name and threshold ────────────────────────────────────────────
@dataclass
class CorpusOutput:
    value: float | None
    details: dict[str, Any] = field(default_factory=dict)
    per_sample: dict[str, float] = field(default_factory=dict)


@dataclass
class BoundMetric:
    info: MetricInfo
    name: str
    params: dict[str, Any] = field(default_factory=dict)
    threshold: float | None = None

    @property
    def call_params(self) -> dict[str, Any]:
        return {**self.info.params, **self.params, **self.info.preset}

    def _wants_ctx(self) -> bool:
        return "ctx" in inspect.signature(self.info.fn).parameters

    def missing(self, sample: Sample) -> list[str]:
        missing = [f for f in self.info.requires if not sample.has(f)]
        if self.info.requires_any and not any(sample.has(f) for f in self.info.requires_any):
            missing.append(" or ".join(self.info.requires_any))
        return missing

    def passed(self, value: float | None) -> bool | None:
        if self.threshold is None or value is None:
            return None
        return value >= self.threshold if self.info.higher_is_better else value <= self.threshold

    def score(self, sample: Sample, ctx: MetricContext | None = None) -> Score:
        if self.info.level != "sample":
            raise TypeError(f"{self.name} is a corpus metric")
        missing = self.missing(sample)
        if missing:
            return Score(
                metric=self.name, skipped=True, reason=f"sample has no {', '.join(missing)}"
            )
        kwargs = self.call_params
        if self._wants_ctx():
            kwargs["ctx"] = ctx or MetricContext()
        try:
            raw = self.info.fn(sample, **kwargs)
        except GuageError:
            raise
        except Exception as exc:
            return Score(metric=self.name, error=f"{type(exc).__name__}: {exc}")
        return self._to_score(raw)

    def _to_score(self, raw: Any) -> Score:
        if raw is None:
            return Score(metric=self.name, skipped=True, reason="not applicable to this sample")
        if isinstance(raw, Score):
            raw.metric = self.name
            if raw.passed is None:
                raw.passed = self.passed(raw.value)
            return raw
        details: dict[str, Any] = {}
        if isinstance(raw, tuple):
            raw, details = raw[0], dict(raw[1])
        value = _finite(raw)
        if value is None:
            return Score(
                metric=self.name, skipped=True, reason="undefined for this sample", details=details
            )
        reason = details.pop("reason", None)
        return Score(
            metric=self.name, value=value, passed=self.passed(value), reason=reason, details=details
        )

    def compute(self, samples: list[Sample], ctx: MetricContext | None = None) -> CorpusOutput:
        if self.info.level != "corpus":
            raise TypeError(f"{self.name} is a sample metric")
        usable = [s for s in samples if not self.missing(s)]
        if not usable:
            return CorpusOutput(None, {"reason": "no sample has the required fields"})
        kwargs = self.call_params
        if self._wants_ctx():
            kwargs["ctx"] = ctx or MetricContext()
        raw = self.info.fn(usable, **kwargs)
        if isinstance(raw, CorpusOutput):
            raw.details.setdefault("n", len(usable))
            return raw
        details: dict[str, Any] = {}
        if isinstance(raw, tuple):
            raw, details = raw[0], dict(raw[1])
        details.setdefault("n", len(usable))
        return CorpusOutput(_finite(raw), details)


def _finite(raw: Any) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return 1.0 if raw else 0.0
    value = float(raw)
    return value if math.isfinite(value) else None


def resolve(
    spec: str | dict[str, Any] | BoundMetric, registry: MetricRegistry = REGISTRY
) -> BoundMetric:
    """Turn ``"recall@5"``, ``"bleu"`` or ``{"name": "rouge", "params": {...}, "threshold": 0.4, "as": "x"}``
    into a bound metric, validating parameters."""
    if isinstance(spec, BoundMetric):
        return spec
    params: dict[str, Any] = {}
    threshold: float | None = None
    display: str | None = None
    if isinstance(spec, dict):
        if "name" not in spec:
            raise GuageError("GK-METRIC-002", f"metric entry without a name: {spec}")
        name = str(spec["name"])
        params = dict(spec.get("params") or {})
        threshold = spec.get("threshold")
        display = spec.get("as")
    else:
        name = str(spec)
    base = name
    if "@" in name and name not in registry:
        base, _, k = name.partition("@")
        try:
            params.setdefault("k", int(k))
        except ValueError as exc:
            raise GuageError(
                "GK-METRIC-002", f"{name}: the value after @ must be an integer"
            ) from exc
    info = registry.get(base)
    unknown = set(params) - set(info.params)
    if unknown:
        raise GuageError(
            "GK-METRIC-002",
            f"{base} has no parameter {', '.join(sorted(unknown))}",
            hint=f"parameters: {', '.join(info.params) or 'none'}",
        )
    return BoundMetric(
        info=info,
        name=display or name,
        params=params,
        threshold=float(threshold) if threshold is not None else None,
    )


def list_metrics(family: str | None = None) -> list[dict[str, Any]]:
    """Every registered metric's declaration (what ``guage metrics list`` prints)."""
    _ensure_builtins()
    return [m.describe() for m in REGISTRY.all() if family is None or m.family == family]


def get_metric(name: str) -> MetricInfo:
    """The declaration (:class:`MetricInfo`) of a registered metric. Raises ``GK-METRIC-001`` for unknown names,
    suggesting the closest match."""
    _ensure_builtins()
    return REGISTRY.get(name)


def _ensure_builtins() -> None:
    import guage_kit.metrics  # noqa: F401  (registers the built-in families)


def _closest(name: str, options: list[str]) -> str | None:
    import difflib

    match = difflib.get_close_matches(name, options, n=1, cutoff=0.6)
    return match[0] if match else None


__all__ = [
    "REGISTRY",
    "BoundMetric",
    "CorpusOutput",
    "MetricContext",
    "MetricInfo",
    "MetricRegistry",
    "corpus_metric",
    "get_metric",
    "list_metrics",
    "metric",
    "resolve",
]
