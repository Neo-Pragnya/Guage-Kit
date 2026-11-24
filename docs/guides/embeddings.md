---
title: Embeddings
description: Evaluate embedding models with STS correlation and representation geometry, and use embedders for semantic similarity metrics.
---

# Embeddings

Two things are covered here: evaluating an **embedding model**, and using an **embedder** inside other metrics.

## Embedders

| Embedder | How to get it | Use |
| --- | --- | --- |
| `HashingEmbedder` | built in; `embedder="hashing"` (also `"builtin"`, `"offline"`) | offline and deterministic: hashed character 3–5-grams and words, 1024 dimensions. Good for near-duplicates and lexical similarity. No download |
| `SentenceTransformerEmbedder` | `pip install "guage-kit[embeddings]"`; `embedder="<model name>"`, e.g. `sentence-transformers/all-MiniLM-L6-v2` | real semantic similarity; downloads the model on first use |
| your own | any object with `name` and `embed(texts) -> list[list[float]]` | an embedding API, a cached index |

Pass one with `evaluate(..., embedder=...)` or `embedder:` in `guage.yaml`. Metrics that need an embedder and get none
use the hashing embedder.

## Semantic similarity metrics

| Metric | Value |
| --- | --- |
| `semantic_similarity` | cosine between output and the closest reference (clipped at 0) |
| `bertscore` | greedy token-embedding matching F1, without idf weighting or baseline rescaling. Uses token embeddings with a sentence-transformers embedder; with the hashing embedder it falls back to word vectors |
| `answer_relevancy` | uses the embedder when one is configured (see [RAG](rag.md)) |

## Evaluating an embedding model

Semantic textual similarity: each sample is a pair, either two texts (`input` and `output`) or two vectors
(`embeddings` with keys `a` and `b`), and a gold similarity in `expected` on any scale.

```python
import guage_kit as gk
from guage_kit.metrics.semantic import HashingEmbedder

data = [gk.Sample(id=str(i), input=a, output=b, expected=g) for i, (a, b, g) in enumerate([
    ("A man is playing guitar.", "A person plays a guitar.", 4.6),
    ("A cat sleeps on the sofa.", "The kitten naps on a couch.", 4.0),
    ("Stocks fell sharply today.", "A dog runs in the park.", 0.2),
    ("The train is late.", "The train arrived late.", 4.2),
])]
run = gk.evaluate(data, ["sts_spearman", "sts_pearson", "embedding_cosine"], embedder=HashingEmbedder())
print({k: round(v.value, 3) for k, v in run.summaries.items()})
```

```text
{'embedding_cosine': 0.311, 'sts_spearman': 0.8, 'sts_pearson': 0.849}
```

Replace `HashingEmbedder()` with the model under test, or precompute vectors and put them in `embeddings`.

| Metric | Value |
| --- | --- |
| `sts_spearman` | rank correlation between cosine and gold similarity (the standard STS score) |
| `sts_pearson` | linear correlation |
| `embedding_cosine` | per-pair cosine |
| `alignment` | mean squared distance between normalised positive pairs (lower: pairs land closer). Wang and Isola (2020) |
| `uniformity` | log of the mean Gaussian potential between all vectors (lower: vectors spread over the sphere). Wang and Isola (2020) |
| `anisotropy` | mean cosine between unrelated vectors (near 0 is isotropic; near 1 means everything looks alike). Ethayarajh (2019) |

`uniformity` and `anisotropy` sample at most `max_pairs` (default 5000) pairs with a fixed seed.

Spearman and Pearson are tested against SciPy.
