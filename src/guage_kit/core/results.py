"""What an evaluation produces: per-sample scores, per-metric summaries, slices, a gate verdict and provenance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

Verdict = Literal["PASS", "WARN", "REVIEW", "BLOCK"]


class Score(BaseModel):
    """One metric's result for one sample."""

    metric: str
    value: float | None = None  # None: skipped or errored
    passed: bool | None = None  # set when the metric has a threshold
    skipped: bool = False
    error: str | None = None
    reason: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class SampleResult(BaseModel):
    """One sample's outcome in a run: its input, output and expected value as evaluated, its tags, a
    :class:`Score` per metric, the target's error if it failed, and its latency."""

    sample_id: str
    input: Any = None
    output: Any = None
    expected: Any = None
    tags: list[str] = Field(default_factory=list)
    scores: dict[str, Score] = Field(default_factory=dict)
    target_error: str | None = None
    latency_ms: float | None = None
    repeats: list[Any] = Field(
        default_factory=list
    )  # extra outputs when a target ran more than once

    @property
    def failed_metrics(self) -> list[str]:
        return [m for m, s in self.scores.items() if s.passed is False]


class MetricSummary(BaseModel):
    """Aggregate of one metric over a run (or a slice of it)."""

    metric: str
    family: str = ""
    description: str = ""
    higher_is_better: bool = True
    level: Literal["sample", "corpus"] = "sample"
    n: int = 0
    skipped: int = 0
    errors: int = 0
    value: float | None = (
        None  # the headline number: mean for sample metrics, the corpus value otherwise
    )
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    min: float | None = None
    max: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    threshold: float | None = None
    pass_rate: float | None = None
    histogram: list[int] = Field(default_factory=list)  # 10 bins over the observed range
    histogram_range: tuple[float, float] | None = None
    details: dict[str, Any] = Field(
        default_factory=dict
    )  # corpus extras (confusion matrix, reliability bins…)


class GateRule(BaseModel):
    """A quality bar for one metric."""

    metric: str
    min: float | None = None
    max: float | None = None
    on_fail: Literal["block", "warn", "review"] = "block"
    max_drop: float | None = None  # allowed drop versus the baseline (absolute)


class GateCheck(BaseModel):
    """The result of one gate rule: the metric's value, the rule it was checked against, whether it passed and a
    human-readable message."""

    metric: str
    value: float | None
    rule: GateRule
    ok: bool
    message: str


class GateResult(BaseModel):
    """A run's verdict (``PASS``, ``WARN``, ``REVIEW`` or ``BLOCK``), decided by Ananke Plexus's gate policy,
    with every check and the evidence files written for it."""

    verdict: Verdict
    checks: list[GateCheck] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    decided_by: str = "ananke.plexus.evals.policy.apply_gate_policy"

    @property
    def blocks(self) -> bool:
        return self.verdict == "BLOCK"


class Environment(BaseModel):
    """Where a run happened: Guage Kit, Ananke Plexus and Python versions, platform and git state (recorded in
    every run so results can be reproduced and compared fairly)."""

    guage_kit: str
    ananke_plexus: str | None = None
    python: str = ""
    platform: str = ""
    git: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    """A complete, self-describing evaluation run. Saved as ``run.json`` and rendered into reports."""

    schema_: str = Field(default="guage-kit/run@1", alias="schema")
    run_id: str
    name: str = ""
    created_at: str = ""
    duration_s: float = 0.0
    dataset: dict[str, Any] = Field(default_factory=dict)  # name, source, fingerprint, samples
    target: dict[str, Any] = Field(
        default_factory=dict
    )  # what produced the outputs, if Guage Kit ran it
    metrics: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    samples: list[SampleResult] = Field(default_factory=list)
    summaries: dict[str, MetricSummary] = Field(default_factory=dict)
    slices: dict[str, dict[str, MetricSummary]] = Field(default_factory=dict)
    gate: GateResult | None = None
    judge: dict[str, Any] = Field(default_factory=dict)  # judge calls, cache hits, cost
    environment: Environment | None = None
    notes: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    def value(self, metric: str) -> float | None:
        s = self.summaries.get(metric)
        return s.value if s else None

    def scores(self, metric: str) -> list[float]:
        """Per-sample values of a metric (skipped and errored samples left out)."""
        out: list[float] = []
        for sr in self.samples:
            sc = sr.scores.get(metric)
            if sc is not None and sc.value is not None:
                out.append(sc.value)
        return out

    def table(self) -> list[dict[str, Any]]:
        """Summary rows for printing or a DataFrame."""
        return [
            {
                "metric": s.metric,
                "value": s.value,
                "ci_low": s.ci_low,
                "ci_high": s.ci_high,
                "n": s.n,
                "pass_rate": s.pass_rate,
            }
            for s in self.summaries.values()
        ]

    def to_json(self) -> str:
        return self.model_dump_json(indent=2, by_alias=True)

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json() + "\n", encoding="utf-8")
        return p

    @classmethod
    def load(cls, path: str | Path) -> RunResult:
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


__all__ = [
    "Environment",
    "GateCheck",
    "GateResult",
    "GateRule",
    "MetricSummary",
    "RunResult",
    "SampleResult",
    "Score",
    "Verdict",
]
