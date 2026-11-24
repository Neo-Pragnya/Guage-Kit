"""Embedders and semantic-similarity metrics.

Two embedders ship:

- :class:`HashingEmbedder` (built in, offline, deterministic): character n-gram feature hashing. Good for
  near-duplicate and lexical-semantic similarity, available everywhere, no download.
- :class:`SentenceTransformerEmbedder` (``pip install guage-kit[embeddings]``): any sentence-transformers model,
  for real semantic similarity and BERTScore-style token matching.

Anything with ``embed(texts) -> list[list[float]]`` works as an embedder.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Protocol, runtime_checkable

from guage_kit.core.sample import Sample
from guage_kit.errors import GuageError
from guage_kit.metrics import _text as T
from guage_kit.metrics.registry import MetricContext, metric

_F = "semantic"


@runtime_checkable
class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class HashingEmbedder:
    """Offline embedder: hashed character 3–5-grams and words, sublinear tf, L2-normalised."""

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim
        self.name = f"hashing-{dim}"

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        toks = T.tokens(text)
        feats: list[str] = [f"w:{t}" for t in toks]
        padded = f" {' '.join(toks)} "
        for n in (3, 4, 5):
            feats.extend(f"c{n}:{padded[i : i + n]}" for i in range(len(padded) - n + 1))
        counts: dict[int, float] = {}
        for f in feats:
            h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "little")
            idx = h % self.dim
            sign = 1.0 if (h >> 63) & 1 else -1.0
            counts[idx] = counts.get(idx, 0.0) + sign
        for idx, c in counts.items():
            v[idx] = math.copysign(1 + math.log(abs(c)), c) if c else 0.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


class SentenceTransformerEmbedder:
    """Embeddings from a sentence-transformers model (Apache-2.0). Models download on first use."""

    def __init__(
        self, model: str = "sentence-transformers/all-MiniLM-L6-v2", device: str | None = None
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise GuageError(
                "GK-METRIC-003",
                "sentence-transformers is not installed",
                hint="pip install 'guage-kit[embeddings]'",
            ) from exc
        self.name = model
        self._model: Any = SentenceTransformer(model, device=device)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._model.encode(texts, normalize_embeddings=True)]

    def token_embed(self, texts: list[str]) -> list[list[list[float]]]:
        out = self._model.encode(texts, output_value="token_embeddings")
        return [[list(map(float, t)) for t in seq] for seq in out]


def make_embedder(spec: str | None) -> Embedder | None:
    """``"hashing"`` → :class:`HashingEmbedder`; any other string → a sentence-transformers model name."""
    if not spec:
        return None
    if spec in ("hashing", "builtin", "offline"):
        return HashingEmbedder()
    return SentenceTransformerEmbedder(spec)


def _embedder(ctx: MetricContext | None) -> Embedder:
    return (ctx.embedder if ctx and ctx.embedder is not None else None) or HashingEmbedder()


@metric("semantic_similarity", family=_F, requires=("output", "expected"), needs_embedder=True)
def semantic_similarity(
    sample: Sample, *, ctx: MetricContext | None = None
) -> tuple[float, dict[str, str]]:
    """Cosine similarity between output and the closest reference, using the run's embedder (hashing if none)."""
    emb = _embedder(ctx)
    vecs = emb.embed([sample.output_text, *sample.expected_texts])
    best = max(cosine(vecs[0], v) for v in vecs[1:])
    return max(0.0, best), {"embedder": emb.name}


@metric(
    "bertscore",
    family=_F,
    requires=("output", "expected"),
    needs_embedder=True,
    extra="embeddings",
    reference="Zhang et al. (2020), BERTScore",
)
def bertscore(
    sample: Sample, *, ctx: MetricContext | None = None
) -> tuple[float, dict[str, float]]:
    """Greedy token-embedding matching F1 (BERTScore without idf or baseline rescaling).

    Needs an embedder with ``token_embed`` (a sentence-transformers model). The built-in hashing embedder falls back
    to word-level matching with hashed word vectors.
    """
    emb = _embedder(ctx)
    best = (0.0, 0.0, 0.0)
    for ref in sample.expected_texts:
        if hasattr(emb, "token_embed"):
            cand, refv = emb.token_embed([sample.output_text, ref])
        else:
            cand = emb.embed(T.tokens(sample.output_text)) if T.tokens(sample.output_text) else []
            refv = emb.embed(T.tokens(ref)) if T.tokens(ref) else []
        if not cand or not refv:
            continue
        r = sum(max(cosine(x, y) for y in cand) for x in refv) / len(refv)
        p = sum(max(cosine(x, y) for y in refv) for x in cand) / len(cand)
        f = T.f1(p, r)
        if f > best[2]:
            best = (p, r, f)
    return best[2], {"precision": round(best[0], 4), "recall": round(best[1], 4)}
