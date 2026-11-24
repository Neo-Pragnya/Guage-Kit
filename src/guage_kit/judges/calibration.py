"""Can you trust the judge? Agreement between a judge and human labels, and between judges.

Before a judge gates a release, grade a labelled sample and check agreement here (``guage judge calibrate``):
quadratic-weighted kappa and Spearman correlation for graded scores, exact and within-one agreement, mean absolute
error and the judge's systematic bias (does it grade more leniently than people?). Ananke's
``judge_human_agreement`` is reported alongside for continuity with Ananke evidence.
"""

from __future__ import annotations

from typing import Any


def weighted_kappa(a: list[int], b: list[int], *, weights: str = "quadratic") -> float | None:
    """Cohen's weighted kappa between two raters' integer grades (``quadratic`` or ``linear`` weights):
    agreement beyond chance, where near misses count partly. None when the lists are empty or differ in length."""
    if not a or len(a) != len(b):
        return None
    cats = sorted(set(a) | set(b))
    if len(cats) < 2:
        return 1.0 if a == b else 0.0
    idx = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b, strict=True):
        obs[idx[x]][idx[y]] += 1
    n = len(a)
    ra = [sum(row) for row in obs]
    cb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    num = den = 0.0
    for i in range(k):
        for j in range(k):
            d = (i - j) ** 2 if weights == "quadratic" else abs(i - j)
            w = d / ((k - 1) ** 2 if weights == "quadratic" else (k - 1))
            num += w * obs[i][j]
            den += w * ra[i] * cb[j] / n
    return 1.0 - num / den if den else 1.0


def agreement(judge: list[float], human: list[float]) -> dict[str, Any]:
    """Agreement statistics between judge scores and human scores on the same scale."""
    from guage_kit.metrics.embeddings import pearson, spearman

    n = len(judge)
    if n == 0 or n != len(human):
        raise ValueError("judge and human scores must be non-empty and the same length")
    ji = [round(x) for x in judge]
    hi = [round(x) for x in human]
    out: dict[str, Any] = {
        "n": n,
        "exact_agreement": sum(1 for x, y in zip(ji, hi, strict=True) if x == y) / n,
        "within_one": sum(1 for x, y in zip(ji, hi, strict=True) if abs(x - y) <= 1) / n,
        "mae": sum(abs(x - y) for x, y in zip(judge, human, strict=True)) / n,
        "bias": sum(x - y for x, y in zip(judge, human, strict=True)) / n,
        "quadratic_kappa": weighted_kappa(ji, hi),
        "spearman": spearman(list(judge), list(human)),
        "pearson": pearson(list(judge), list(human)),
    }
    try:
        from ananke.plexus.evals.evaluators.meta.calibration import judge_human_agreement

        out["ananke"] = judge_human_agreement(list(judge), list(human))
    except Exception:  # noqa: S110 - Ananke's view is an extra, never required
        pass
    k = out["quadratic_kappa"]
    out["verdict"] = (
        "strong"
        if k is not None and k >= 0.8
        else "moderate"
        if k is not None and k >= 0.6
        else "weak"
    )
    return out


def position_consistency(verdicts: list[Any]) -> float | None:
    """Share of pairwise verdicts that held when the two responses swapped places (1 means no position bias)."""
    if not verdicts:
        return None
    return sum(1 for v in verdicts if v.consistent) / len(verdicts)


__all__ = ["agreement", "position_consistency", "weighted_kappa"]
