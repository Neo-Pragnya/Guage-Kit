"""Information-retrieval metrics over ranked ids: precision, recall, hit rate, MRR, MAP, nDCG and R-precision.

A sample needs ``retrieved_ids`` (the ranking, best first) and either ``relevant_ids`` (binary relevance) or
``relevance`` (graded: id → gain). The run summary is the mean over samples, which is the standard definition of
MAP and mean nDCG. ``recall@5`` style names set ``k``; ``k=0`` means the whole ranking.
"""

from __future__ import annotations

import math

from guage_kit.core.sample import Sample
from guage_kit.metrics.registry import metric

_F = "retrieval"
_REQ = ("retrieved_ids",)
_ANY = ("relevant_ids", "relevance")


def _relevant(sample: Sample) -> set[str]:
    if sample.relevant_ids:
        return set(sample.relevant_ids)
    return {k for k, g in sample.relevance.items() if g > 0}


def _cut(ids: list[str], k: int) -> list[str]:
    return ids[:k] if k > 0 else ids


@metric("precision", family=_F, requires=_REQ, requires_any=_ANY)
def precision_at_k(sample: Sample, *, k: int = 10) -> float:
    """Share of the top-k retrieved ids that are relevant (divides by k, even when fewer were retrieved)."""
    rel = _relevant(sample)
    top = _cut(sample.retrieved_ids, k)
    denom = k if k > 0 else len(top)
    return sum(1 for d in top if d in rel) / denom if denom else 0.0


@metric("recall", family=_F, requires=_REQ, requires_any=_ANY)
def recall_at_k(sample: Sample, *, k: int = 10) -> float | None:
    """Share of the relevant ids found in the top k."""
    rel = _relevant(sample)
    if not rel:
        return None
    return len(rel & set(_cut(sample.retrieved_ids, k))) / len(rel)


@metric("hit_rate", family=_F, requires=_REQ, requires_any=_ANY)
def hit_rate(sample: Sample, *, k: int = 10) -> float:
    """1 when at least one relevant id is in the top k (also called success@k)."""
    rel = _relevant(sample)
    return float(any(d in rel for d in _cut(sample.retrieved_ids, k)))


@metric("mrr", family=_F, requires=_REQ, requires_any=_ANY, reference="Voorhees (1999)")
def mrr(sample: Sample, *, k: int = 0) -> float:
    """Reciprocal rank of the first relevant id (0 when none is retrieved). The run value is the mean (MRR)."""
    rel = _relevant(sample)
    for rank, d in enumerate(_cut(sample.retrieved_ids, k), 1):
        if d in rel:
            return 1.0 / rank
    return 0.0


@metric("average_precision", family=_F, requires=_REQ, requires_any=_ANY)
def average_precision(sample: Sample, *, k: int = 0) -> float | None:
    """Average of precision@i at each rank i holding a relevant id, over all relevant ids. The mean is MAP."""
    rel = _relevant(sample)
    if not rel:
        return None
    hits = 0
    total = 0.0
    for i, d in enumerate(_cut(sample.retrieved_ids, k), 1):
        if d in rel:
            hits += 1
            total += hits / i
    return total / len(rel)


@metric(
    "ndcg", family=_F, requires=_REQ, requires_any=_ANY, reference="Järvelin & Kekäläinen (2002)"
)
def ndcg(sample: Sample, *, k: int = 10, exponential: bool = False) -> float | None:
    """Normalised discounted cumulative gain at k. Uses graded ``relevance`` when present (exponential gain optional)."""
    gains = dict(sample.relevance) if sample.relevance else dict.fromkeys(sample.relevant_ids, 1.0)
    if not any(g > 0 for g in gains.values()):
        return None

    def gain(g: float) -> float:
        return (2**g - 1) if exponential else g

    dcg = sum(
        gain(gains.get(d, 0.0)) / math.log2(i + 2)
        for i, d in enumerate(_cut(sample.retrieved_ids, k))
    )
    ideal = sorted(gains.values(), reverse=True)
    ideal = ideal[:k] if k > 0 else ideal
    idcg = sum(gain(g) / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg else None


@metric("r_precision", family=_F, requires=_REQ, requires_any=_ANY)
def r_precision(sample: Sample) -> float | None:
    """Precision at R, where R is the number of relevant ids."""
    rel = _relevant(sample)
    if not rel:
        return None
    top = sample.retrieved_ids[: len(rel)]
    return sum(1 for d in top if d in rel) / len(rel)
