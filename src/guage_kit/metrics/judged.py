"""Judge-backed metrics: grade each sample against a criterion with the run's judge.

``judge`` with ``criterion: correctness`` (or helpfulness, groundedness, … or your own rubric) returns the judge's
1–5 grade normalised to 0–1, with its reasoning in the details. Use ``as:`` to run several criteria in one run::

    metrics:
      - {name: judge, params: {criterion: correctness}, as: judge_correctness, threshold: 0.75}
      - {name: judge, params: {criterion: groundedness}, as: judge_groundedness}
"""

from __future__ import annotations

from typing import Any

from guage_kit.core.results import Score
from guage_kit.core.sample import Sample
from guage_kit.errors import GuageError
from guage_kit.metrics.registry import MetricContext, metric


@metric(
    "judge",
    family="judge",
    requires=("output",),
    deterministic=False,
    needs_judge=True,
    reference="Zheng et al. (2023), LLM-as-a-judge; Liu et al. (2023), G-Eval",
)
def judge(
    sample: Sample, *, criterion: Any = "helpfulness", ctx: MetricContext | None = None
) -> Score:
    """A judge's grade on a criterion (correctness, helpfulness, relevance, groundedness, completeness, coherence,
    conciseness, instruction_following, harmlessness, tone, factual_consistency, or a custom rubric)."""
    if ctx is None or ctx.judge is None:
        raise GuageError(
            "GK-JUDGE-001",
            "the judge metric needs a judge",
            hint="evaluate(..., judge='anthropic:claude-opus-5-5') or judge: in guage.yaml ('heuristic' works offline)",
        )
    v = ctx.judge.grade(sample, criterion)
    return Score(
        metric="judge",
        value=v.score,
        reason=v.reason,
        details={
            "raw_score": v.raw_score,
            "samples": v.samples,
            "cached": v.cached,
            "judge": ctx.judge.name,
            "criterion": criterion
            if isinstance(criterion, str)
            else getattr(criterion, "name", str(criterion)),
        },
    )
