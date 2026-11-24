"""Compare two runs on the same data: which metrics really moved, which samples got worse, and is it significant?

For every sample-level metric both runs share, the comparison pairs samples by id and reports the mean difference
with a paired-bootstrap interval, a permutation-test p-value (Holm-adjusted across metrics), a sign test and an
effect size. Corpus metrics get their difference only (no per-sample test exists for them). A change is called
an improvement or a regression only when it is significant *and* larger than ``min_effect``.

:func:`pairwise` asks a judge which output is better, sample by sample, in both orders.
"""

from __future__ import annotations

import random
from typing import Any, Literal

from pydantic import BaseModel, Field

from guage_kit import stats
from guage_kit.core.results import RunResult
from guage_kit.errors import GuageError

Direction = Literal["improved", "regressed", "unchanged", "inconclusive", "changed"]


class MetricDelta(BaseModel):
    metric: str
    level: str = "sample"
    higher_is_better: bool = True
    a: float | None = None
    b: float | None = None
    delta: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: float | None = None
    p_adjusted: float | None = None
    effect_size: float | None = None
    wins: int = 0
    losses: int = 0
    ties: int = 0
    n: int = 0
    direction: Direction = "inconclusive"


class SampleDelta(BaseModel):
    sample_id: str
    metric: str
    a: float
    b: float
    delta: float
    input: Any = None
    output_a: Any = None
    output_b: Any = None


class Comparison(BaseModel):
    schema_: str = Field(default="guage-kit/comparison@1", alias="schema")
    run_a: dict[str, Any]
    run_b: dict[str, Any]
    same_data: bool
    common_samples: int
    metrics: dict[str, MetricDelta] = Field(default_factory=dict)
    regressions: list[SampleDelta] = Field(default_factory=list)  # worst sample-level drops
    improvements: list[SampleDelta] = Field(default_factory=list)
    pairwise: dict[str, Any] | None = None
    alpha: float = 0.05
    min_effect: float = 0.0

    model_config = {"populate_by_name": True}

    @property
    def regressed(self) -> list[str]:
        return [m for m, d in self.metrics.items() if d.direction == "regressed"]

    @property
    def improved(self) -> list[str]:
        return [m for m, d in self.metrics.items() if d.direction == "improved"]


def _brief(run: RunResult) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "name": run.name,
        "created_at": run.created_at,
        "dataset": run.dataset,
        "target": run.target,
    }


def compare(
    a: RunResult,
    b: RunResult,
    *,
    metrics: list[str] | None = None,
    alpha: float = 0.05,
    min_effect: float = 0.0,
    n_resamples: int = 2000,
    seed: int = 0,
    top: int = 10,
) -> Comparison:
    """Compare run ``b`` (candidate) against run ``a`` (baseline)."""
    by_a = {s.sample_id: s for s in a.samples}
    by_b = {s.sample_id: s for s in b.samples}
    common = [sid for sid in by_a if sid in by_b]
    if not common:
        raise GuageError(
            "GK-RUN-002", "the runs share no sample ids", hint="compare runs over the same dataset"
        )
    names = metrics or [m for m in a.summaries if m in b.summaries]
    out = Comparison(
        run_a=_brief(a),
        run_b=_brief(b),
        same_data=(a.dataset.get("input_fingerprint") or a.dataset.get("fingerprint"))
        == (b.dataset.get("input_fingerprint") or b.dataset.get("fingerprint")),
        common_samples=len(common),
        alpha=alpha,
        min_effect=min_effect,
    )
    p_values: dict[str, float] = {}
    sample_deltas: list[SampleDelta] = []
    for m in names:
        sa, sb = a.summaries.get(m), b.summaries.get(m)
        if sa is None or sb is None:
            continue
        hib = sa.higher_is_better
        d = MetricDelta(metric=m, level=sa.level, higher_is_better=hib, a=sa.value, b=sb.value)
        if sa.value is not None and sb.value is not None:
            d.delta = sb.value - sa.value
        pairs: list[tuple[str, float, float]] = []
        for sid in common:
            sc_a = by_a[sid].scores.get(m)
            sc_b = by_b[sid].scores.get(m)
            if sc_a and sc_b and sc_a.value is not None and sc_b.value is not None:
                pairs.append((sid, sc_a.value, sc_b.value))
        d.n = len(pairs)
        if sa.level == "sample" and len(pairs) >= 2:
            xs = [p[1] for p in pairs]
            ys = [p[2] for p in pairs]
            pb = stats.paired_bootstrap(xs, ys, n_resamples=n_resamples, seed=seed)
            d.delta = pb["delta"]
            d.ci_low, d.ci_high = pb["ci_low"], pb["ci_high"]
            d.p_value = stats.permutation_test(xs, ys, seed=seed)
            st = stats.sign_test(xs, ys)
            d.wins, d.losses, d.ties = int(st["wins"]), int(st["losses"]), int(st["ties"])
            es = stats.cohens_d(xs, ys)
            d.effect_size = es if es == es and abs(es) != float("inf") else None
            p_values[m] = d.p_value
            for sid, x, y in pairs:
                if y != x:
                    sample_deltas.append(
                        SampleDelta(
                            sample_id=sid,
                            metric=m,
                            a=x,
                            b=y,
                            delta=y - x,
                            input=by_a[sid].input,
                            output_a=by_a[sid].output,
                            output_b=by_b[sid].output,
                        )
                    )
        out.metrics[m] = d
    for m, adj in stats.holm(p_values, alpha).items():
        out.metrics[m].p_adjusted = adj["p_adjusted"]
    for d in out.metrics.values():
        if d.delta is None:
            continue
        signed = d.delta if d.higher_is_better else -d.delta
        if d.p_adjusted is None:
            # corpus metric: no per-sample test exists, so a change is reported, never called significant
            if d.level == "corpus":
                d.direction = "unchanged" if abs(signed) <= max(min_effect, 1e-9) else "changed"
            else:
                d.direction = "inconclusive"
            continue
        if d.p_adjusted <= alpha and abs(signed) > min_effect:
            d.direction = "improved" if signed > 0 else "regressed"
        elif (
            d.ci_low is not None
            and d.ci_high is not None
            and d.ci_high - d.ci_low < 0.05
            and abs(signed) <= max(min_effect, 0.01)
        ):
            d.direction = "unchanged"
        else:
            d.direction = "inconclusive"

    def worse(sd: SampleDelta) -> float:
        hib = out.metrics[sd.metric].higher_is_better
        return sd.delta if hib else -sd.delta

    sample_deltas.sort(key=worse)
    out.regressions = [s for s in sample_deltas if worse(s) < 0][:top]
    out.improvements = [s for s in reversed(sample_deltas) if worse(s) > 0][:top]
    return out


def pairwise(
    a: RunResult,
    b: RunResult,
    judge: Any,
    *,
    criterion: str = "helpfulness",
    limit: int | None = None,
    seed: int = 0,
) -> dict[str, Any]:
    """Judge each shared sample's two outputs head to head (both orders). Returns b's win rate with a CI."""
    from guage_kit.judges.judge import make_judge

    j = make_judge(judge)
    if j is None:
        raise GuageError("GK-JUDGE-001", "pairwise comparison needs a judge")
    by_b = {s.sample_id: s for s in b.samples}
    rows = []
    shared = [
        s
        for s in a.samples
        if s.sample_id in by_b and s.output is not None and by_b[s.sample_id].output is not None
    ]
    if limit:
        shared = shared[:limit]
    for sa in shared:
        sb = by_b[sa.sample_id]
        ref = sa.expected if isinstance(sa.expected, str) else None
        v = j.pairwise(
            question=str(sa.input),
            a=str(sa.output),
            b=str(sb.output),
            criterion=criterion,
            reference=ref,
        )
        rows.append(
            {
                "sample_id": sa.sample_id,
                "winner": v.winner,
                "consistent": v.consistent,
                "reason": v.reason,
            }
        )
    n = len(rows)
    if not n:
        raise GuageError("GK-RUN-002", "no shared samples with outputs in both runs")
    score = [1.0 if r["winner"] == "b" else 0.5 if r["winner"] == "tie" else 0.0 for r in rows]
    lo, hi = stats.bootstrap_ci(score, seed=seed)
    wins = sum(1 for r in rows if r["winner"] == "b")
    losses = sum(1 for r in rows if r["winner"] == "a")
    return {
        "criterion": criterion,
        "judge": j.name,
        "n": n,
        "b_wins": wins,
        "a_wins": losses,
        "ties": n - wins - losses,
        "win_rate": stats.mean(score),
        "ci_low": lo,
        "ci_high": hi,
        "position_consistency": sum(1 for r in rows if r["consistent"]) / n,
        "p_value": stats._binom_two_sided(min(wins, losses), wins + losses),
        "rows": rows if n <= 500 else random.Random(seed).sample(rows, 500),
    }


def regression_gate(comparison: Comparison, rules: list[Any]) -> list[str]:
    """Messages for every rule whose ``max_drop`` the candidate exceeds versus the baseline."""
    problems = []
    for r in rules:
        md = getattr(r, "max_drop", None) if not isinstance(r, dict) else r.get("max_drop")
        metric = r["metric"] if isinstance(r, dict) else r.metric
        if md is None or metric not in comparison.metrics:
            continue
        d = comparison.metrics[metric]
        if d.delta is None:
            continue
        drop = -d.delta if d.higher_is_better else d.delta
        if drop > md:
            problems.append(f"{metric} dropped {drop:.4g} versus the baseline (allowed {md:g})")
    return problems


__all__ = ["Comparison", "MetricDelta", "SampleDelta", "compare", "pairwise", "regression_gate"]
