---
title: RAG
description: Evaluate retrieval and grounded generation separately - ranking metrics, context quality, claim-level faithfulness, citations - offline or with a judge.
---

# Evaluating RAG

A retrieval-augmented system can fail in two places: retrieval brings back the wrong passages, or generation ignores
or embellishes the passages it got. Measure both, separately, so you know which half to fix.

```mermaid
flowchart LR
  Q[question] --> R[retriever] --> C[contexts + retrieved_ids] --> G[generator] --> A[answer]
  C -. retrieval metrics .-> M1[recall@k, MRR, nDCG, context precision/recall]
  A -. generation metrics .-> M2[faithfulness, answer relevancy, correctness, citations]
```

## Retrieval

With ids (`retrieved_ids` plus `relevant_ids` or graded `relevance`), use the ranking metrics:

| Metric | Meaning |
| --- | --- |
| `recall@k` | share of relevant ids found in the top k |
| `precision@k` | share of the top k that is relevant (divides by k) |
| `hit_rate@k` | 1 when anything relevant is in the top k |
| `mrr` | reciprocal rank of the first relevant id (mean over samples) |
| `average_precision` | AP per sample; the mean is MAP |
| `ndcg@k` | normalised DCG; uses graded `relevance` when present (`exponential: true` for 2^g − 1 gain) |
| `r_precision` | precision at R, the number of relevant ids |

Without ids, the context metrics judge the passages by their text:

| Metric | Meaning |
| --- | --- |
| `context_recall` | share of the reference answer's claims that the contexts contain: did retrieval find what was needed? |
| `context_precision` | rank-aware precision of the contexts. A chunk is relevant if its id is in `relevant_ids`, otherwise if it supports the reference answer, otherwise if it overlaps the question |
| `context_relevance` | share of context sentences related to the question (noise in what was retrieved) |

## Generation

| Metric | Meaning |
| --- | --- |
| `faithfulness` | share of the answer's claims that the contexts support (groundedness) |
| `hallucination_rate` | 1 − faithfulness (lower is better) |
| `answer_relevancy` | how directly the answer addresses the question; penalises refusals and answers that only echo the question |
| `answer_correctness` | claim-level F1 between answer and reference; recall only when the reference is four content words or fewer |
| `context_utilization` | share of retrieved chunks the answer draws on |
| `citation_accuracy` | share of `[n]` citations whose cited context (1-based) supports the citing sentence |
| `citation_coverage` | share of answer sentences that carry a citation |

### How faithfulness works

The answer is split into claims (sentences, further split at "and/but/while/whereas" between clauses; citation
markers such as `[1]` are removed). Each claim is checked against the contexts:

- **`method: lexical`** (default, offline, deterministic): support is the share of the claim's content words found in
  the evidence, with content bigrams weighted in (0.7 unigram, 0.3 bigram). A claim containing a number the evidence
  doesn't contain is capped at 0.5. A claim is supported at `threshold` (default 0.6) or above.
- **`method: judge`**: the run's judge decides whether the evidence supports each claim (supported 1, partial 0.5,
  unsupported 0), and 0.5 or above counts.

```yaml
metrics:
  - faithfulness                                       # lexical
  - {name: faithfulness, params: {method: judge}, as: faithfulness_judged}
judge: anthropic:claude-opus-5-5
```

The lexical method is transparent and free. It catches invented facts, wrong numbers and answers padded with
unsupported detail. It cannot recognise a paraphrase that shares no words with the source. Use the judge method
when your answers paraphrase heavily, and compare the two on a sample before trusting either.

Every faithfulness score carries a claim table, which the report shows under each sample:

```python
run.samples[0].scores["faithfulness"].details["claims"]
# [{'claim': 'Annual Pro subscriptions can be refunded in full within 14 days of purchase.',
#   'supported': True, 'support': 1.0}]
```

`context_recall`, `answer_correctness` and `citation_accuracy` use the same lexical support function, with
`threshold` as a parameter.

## A complete example

A toy pipeline that reports what it retrieved:

```python
import guage_kit as gk

KB = {
    "kb-refund": "Annual Pro subscriptions can be refunded in full within 14 days of purchase. Monthly plans are not refunded.",
    "kb-pricing": "Lumen Notes Pro costs 6 dollars per month and includes 100 GB of storage.",
    "kb-sync": "Lumen Notes syncs every 30 seconds when you are online.",
}

def retrieve(question: str, k: int = 2) -> list[str]:
    # toy retriever: rank documents by shared words
    words = set(question.lower().split())
    return sorted(KB, key=lambda d: -len(words & set(KB[d].lower().split())))[:k]

def rag(question: str) -> dict:
    ids = retrieve(question)
    answer = f"{KB[ids[0]].split('.')[0]} [1]."      # pretend generation: quote the top passage
    return {"output": answer, "contexts": [KB[i] for i in ids], "retrieved_ids": ids}

data = gk.Dataset.from_records([
    {"id": "r1", "question": "Can I get a refund on an annual plan?", "ground_truth": "Yes, in full within 14 days of purchase.", "relevant_ids": ["kb-refund"]},
    {"id": "r2", "question": "How much does Pro cost per month?", "ground_truth": "6 dollars per month.", "relevant_ids": ["kb-pricing"]},
    {"id": "r3", "question": "How often does Lumen sync when I am online?", "ground_truth": "Every 30 seconds.", "relevant_ids": ["kb-sync"]},
])
run = gk.evaluate(data, ["recall@2", "mrr", "context_precision", "context_recall",
                         "faithfulness", "answer_correctness", "citation_accuracy"], target=rag)
for name, s in run.summaries.items():
    print(f"{name:18} {s.value:.3f}")
```

```text
recall@2           1.000
mrr                1.000
context_precision  1.000
context_recall     1.000
faithfulness       1.000
answer_correctness 0.667
citation_accuracy  1.000
```

Retrieval is perfect and the answers are grounded, but one answer ("Lumen Notes Pro costs 6 dollars per month and
includes 100 GB of storage") does not match its reference claim by claim. That is the generation step to look at.

In a suite, the same thing is `target: my_package.rag:rag` with the dataset file.

## Tips

- Slice by question type or difficulty (`slices: [difficulty]`) to see where retrieval breaks down.
- Gate on both halves: for example `recall@5 ≥ 0.85` (warn) and `faithfulness ≥ 0.8` (block).
- `guage synth` builds a test set with `relevant_ids` from your own documents. See [Synthetic data](synthetic-data.md).
- The `shuffle_contexts`, `drop_top_context` and `noise_context` perturbations test how the generator copes with
  worse retrieval. See [Robustness](robustness.md).
