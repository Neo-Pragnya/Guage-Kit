"""Runtime metrics: latency, tokens and cost per sample, and tail latency and total cost per run.

Latency comes from ``latency_ms`` (Guage Kit measures it when it runs your target). Tokens and cost come from
``usage``. Cost can also be computed from token counts with a price table: ``prices`` maps a model name to dollars
per million input and output tokens, ``{"my-model": [0.25, 1.25]}``. No prices ship with Guage Kit, because they
change; pass your own.
"""

from __future__ import annotations

from typing import Any

from guage_kit.core.sample import Sample
from guage_kit.errors import GuageError
from guage_kit.metrics.registry import CorpusOutput, corpus_metric, metric

_F = "runtime"


@metric(
    "latency_ms",
    family=_F,
    requires=("latency_ms",),
    higher_is_better=False,
    value_range=(0.0, None),
)
def latency_ms(sample: Sample) -> float | None:
    """Time to produce the output, in milliseconds."""
    return sample.latency_ms


@metric(
    "total_tokens", family=_F, requires=("usage",), higher_is_better=False, value_range=(0.0, None)
)
def total_tokens(sample: Sample) -> float | None:
    """Prompt plus completion tokens."""
    return float(sample.usage.tokens) if sample.usage and sample.usage.tokens is not None else None


def sample_cost(sample: Sample, prices: dict[str, Any] | None = None) -> float | None:
    if sample.usage is None:
        return None
    if sample.usage.cost_usd is not None:
        return sample.usage.cost_usd
    model = str(sample.metadata.get("model") or "")
    if prices and model in prices:
        if sample.usage.prompt_tokens is None and sample.usage.completion_tokens is None:
            return None  # only a total is known: input and output prices differ, so it cannot be priced
        pin, pout = prices[model]
        return (
            (sample.usage.prompt_tokens or 0) * float(pin)
            + (sample.usage.completion_tokens or 0) * float(pout)
        ) / 1e6
    return None


@metric("cost_usd", family=_F, requires=("usage",), higher_is_better=False, value_range=(0.0, None))
def cost_usd(sample: Sample, *, prices: dict[str, Any] | None = None) -> float | None:
    """Cost of the sample in US dollars (from usage, or token counts times your ``prices``)."""
    return sample_cost(sample, prices)


def _percentile(values: list[float], p: float) -> float:
    if not 0 <= p <= 100:
        raise GuageError(
            "GK-METRIC-002", f"percentile {p} is outside 0–100", hint="latency_p95@99 for p99"
        )
    s = sorted(values)
    idx = (len(s) - 1) * p / 100
    lo = int(idx)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


@corpus_metric(
    "latency_p50",
    family=_F,
    requires=("latency_ms",),
    higher_is_better=False,
    value_range=(0.0, None),
)
def latency_p50(samples: list[Sample]) -> float:
    """Median latency (ms)."""
    return _percentile([s.latency_ms or 0.0 for s in samples], 50)


@corpus_metric(
    "latency_p95",
    family=_F,
    requires=("latency_ms",),
    higher_is_better=False,
    value_range=(0.0, None),
)
def latency_p95(samples: list[Sample], *, k: int = 95) -> CorpusOutput:
    """Tail latency (ms) at the k-th percentile (``latency_p95@99`` for p99)."""
    vals = [s.latency_ms or 0.0 for s in samples]
    return CorpusOutput(_percentile(vals, k), {"percentile": k, "max": max(vals)})


@corpus_metric(
    "total_cost_usd",
    family=_F,
    requires=("usage",),
    higher_is_better=False,
    value_range=(0.0, None),
)
def total_cost_usd(samples: list[Sample], *, prices: dict[str, Any] | None = None) -> float | None:
    """Cost of the whole run in US dollars."""
    costs = [c for c in (sample_cost(s, prices) for s in samples) if c is not None]
    return sum(costs) if costs else None
