"""Embedding-model metrics: semantic textual similarity (STS) correlation and representation geometry.

STS samples hold two texts (``input`` and ``output``) or two vectors (``embeddings`` with keys ``a`` and ``b``)
and a gold similarity in ``expected`` (any scale). The metric correlates the model's cosine with the gold scores.
Geometry metrics (alignment, uniformity, anisotropy) follow Wang & Isola (2020) and Ethayarajh (2019).
"""

from __future__ import annotations

import math
import random

from guage_kit.core.sample import Sample
from guage_kit.metrics.registry import MetricContext, corpus_metric, metric
from guage_kit.metrics.semantic import HashingEmbedder, cosine

_F = "embeddings"


def _pair_vectors(
    samples: list[Sample], ctx: MetricContext | None
) -> list[tuple[list[float], list[float], Sample]]:
    out = []
    need_text = [s for s in samples if not ("a" in s.embeddings and "b" in s.embeddings)]
    emb = (ctx.embedder if ctx and ctx.embedder else None) or HashingEmbedder()
    texts: dict[str, list[list[float]]] = {}
    if need_text:
        flat = [t for s in need_text for t in (s.input_text, s.output_text)]
        vecs = emb.embed(flat)
        for i, s in enumerate(need_text):
            texts[s.id] = [vecs[2 * i], vecs[2 * i + 1]]
    for s in samples:
        if "a" in s.embeddings and "b" in s.embeddings:
            out.append((s.embeddings["a"], s.embeddings["b"], s))
        else:
            a, b = texts[s.id]
            out.append((a, b, s))
    return out


def _gold(s: Sample) -> float | None:
    try:
        return float(s.expected)
    except (TypeError, ValueError):
        return None


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def pearson(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 2:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sxy / (sx * sy) if sx and sy else None


def spearman(x: list[float], y: list[float]) -> float | None:
    return pearson(_rank(x), _rank(y))


def _sts(samples: list[Sample], ctx: MetricContext | None) -> tuple[list[float], list[float]]:
    pred, gold = [], []
    for a, b, s in _pair_vectors(samples, ctx):
        g = _gold(s)
        if g is not None:
            pred.append(cosine(a, b))
            gold.append(g)
    return pred, gold


@corpus_metric(
    "sts_spearman",
    family=_F,
    requires=("expected",),
    value_range=(-1.0, 1.0),
    needs_embedder=True,
    reference="Reimers et al. (2016)",
)
def sts_spearman(samples: list[Sample], *, ctx: MetricContext | None = None) -> float | None:
    """Spearman rank correlation between embedding cosine and gold similarity (the standard STS score)."""
    return spearman(*_sts(samples, ctx))


@corpus_metric(
    "sts_pearson", family=_F, requires=("expected",), value_range=(-1.0, 1.0), needs_embedder=True
)
def sts_pearson(samples: list[Sample], *, ctx: MetricContext | None = None) -> float | None:
    """Pearson correlation between embedding cosine and gold similarity."""
    return pearson(*_sts(samples, ctx))


@metric(
    "embedding_cosine",
    family=_F,
    requires_any=("embeddings", "output"),
    value_range=(-1.0, 1.0),
    needs_embedder=True,
)
def embedding_cosine(sample: Sample, *, ctx: MetricContext | None = None) -> float:
    """Cosine of the pair (``embeddings.a``/``b``, or the embedded ``input`` and ``output``)."""
    a, b, _ = _pair_vectors([sample], ctx)[0]
    return cosine(a, b)


@corpus_metric(
    "alignment",
    family=_F,
    requires_any=("embeddings", "output"),
    higher_is_better=False,
    needs_embedder=True,  # embeds input and output when no vectors are given
    value_range=(0.0, 4.0),
    reference="Wang & Isola (2020)",
)
def alignment(samples: list[Sample], *, ctx: MetricContext | None = None) -> float:
    """Mean squared distance between normalised positive pairs (lower: paired texts land closer)."""
    vals = []
    for a, b, _ in _pair_vectors(samples, ctx):
        na, nb = _unit(a), _unit(b)
        vals.append(sum((x - y) ** 2 for x, y in zip(na, nb, strict=False)))
    return sum(vals) / len(vals)


@corpus_metric(
    "uniformity",
    family=_F,
    requires_any=("embeddings", "output"),
    higher_is_better=False,
    needs_embedder=True,  # embeds input and output when no vectors are given
    value_range=(None, 0.0),
    reference="Wang & Isola (2020)",
)
def uniformity(
    samples: list[Sample],
    *,
    t: float = 2.0,
    max_pairs: int = 5000,
    ctx: MetricContext | None = None,
) -> float | None:
    """log E[exp(−t‖u−v‖²)] over all vectors (lower: embeddings spread over the sphere)."""
    vecs = [_unit(v) for a, b, _ in _pair_vectors(samples, ctx) for v in (a, b)]
    pairs = [(i, j) for i in range(len(vecs)) for j in range(i + 1, len(vecs))]
    if not pairs:
        return None
    if len(pairs) > max_pairs:
        pairs = random.Random(0).sample(pairs, max_pairs)
    vals = [
        math.exp(-t * sum((x - y) ** 2 for x, y in zip(vecs[i], vecs[j], strict=False)))
        for i, j in pairs
    ]
    return math.log(sum(vals) / len(vals))


@corpus_metric(
    "anisotropy",
    family=_F,
    requires_any=("embeddings", "output"),
    higher_is_better=False,
    needs_embedder=True,  # embeds input and output when no vectors are given
    value_range=(-1.0, 1.0),
    reference="Ethayarajh (2019)",
)
def anisotropy(
    samples: list[Sample], *, max_pairs: int = 5000, ctx: MetricContext | None = None
) -> float | None:
    """Mean cosine between unrelated vectors (near 0 is isotropic; near 1 means everything looks alike)."""
    vecs = [v for a, b, _ in _pair_vectors(samples, ctx) for v in (a, b)]
    pairs = [(i, j) for i in range(0, len(vecs), 2) for j in range(1, len(vecs), 2) if j != i + 1]
    if not pairs:
        return None
    if len(pairs) > max_pairs:
        pairs = random.Random(0).sample(pairs, max_pairs)
    return sum(cosine(vecs[i], vecs[j]) for i, j in pairs) / len(pairs)


def _unit(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]
