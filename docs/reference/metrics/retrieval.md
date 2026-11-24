---
title: Retrieval metrics
description: "Ranked-retrieval metrics over document ids: precision, recall, hit rate, MRR, MAP, nDCG."
---

# Retrieval metrics

> [!NOTE]
> Generated from the metric registry and the metric cards (`guage_kit/metrics/cards/`). Every example
> on this page is run by the test suite, so the numbers are what the metric really returns.

Ranked-retrieval metrics over document ids: precision, recall, hit rate, MRR, MAP, nDCG.

| metric | in one line |
| --- | --- |
| [`average_precision`](#average_precision) | The average of precision@i over the ranks i that hold a relevant id, divided by all relevant ids; the mean over samples is MAP. |
| [`hit_rate`](#hit_rate) | 1 when at least one relevant id appears in the top k retrieved, else 0; the mean over samples is the share of queries with a hit (success@k). |
| [`mrr`](#mrr) | The reciprocal of the rank of the first relevant id (1 at rank 1, 0.5 at rank 2, 0 if none); the mean over samples is mean reciprocal rank. |
| [`ndcg`](#ndcg) | Normalised discounted cumulative gain at k, which rewards putting the most relevant ids first, on a 0–1 scale where 1 is the ideal ordering. |
| [`precision`](#precision) | The share of the top k retrieved ids that are relevant (precision@k). |
| [`r_precision`](#r_precision) | Precision at rank R, where R is the number of relevant ids for the query, so the cut-off adapts to each query. |
| [`recall`](#recall) | The share of the relevant ids that appear in the top k retrieved (recall@k). |

## average_precision

*The average of precision@i over the ranks i that hold a relevant id, divided by all relevant ids; the mean over samples is MAP.*

**Level:** sample · **Range:** 0 to 1, higher is better · **Needs:** `retrieved_ids`, `relevant_ids` or `relevance` · **Deterministic:** yes

**What it measures**

Ranking quality over all relevant items at once. It answers "are the relevant items found, and found early?" It rewards both recall and good ordering, which makes it the standard single-number summary for ranked retrieval with binary relevance.

**How it is computed**

1. The relevant set is `relevant_ids`; if that is empty, every id in `relevance` with a gain above 0.
   A sample with no relevant ids is skipped.
2. Walk the ranking (cut to k when `k > 0`; by default the whole ranking). At each rank i holding a relevant
   id, record precision@i = relevant ids seen so far ÷ i.
3. Sum those precisions and divide by the **total** number of relevant ids, so relevant ids that were never
   retrieved contribute 0.
4. The run value is the mean over samples, which is mean average precision (MAP).

```text
AP  = (1/|relevant|) Σ_{i : retrieved[i] ∈ relevant} P@i,     P@i = |relevant ∩ retrieved[1..i]| / i
MAP = (1/|Q|) Σ_q AP_q
```

**Inputs:** `retrieved_ids` (best first) and `relevant_ids` or `relevance` (any gain > 0 counts as relevant).

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `k` | `0` | Cut-off rank (default 0 = the whole ranking). `average_precision@10` sets `k: 10`; the denominator stays the total number of relevant ids. |

**How to read it**

0–1, higher is better. 1.0 means all relevant ids are retrieved and ranked above every irrelevant one. It falls both when relevant items are missing and when they are ranked low. Typical ad hoc search systems score well below 0.5 on hard collections; compare systems on the same labels rather than against absolute targets.

**Use it when**

- Comparing retrievers on queries with several relevant documents.
- A single number that balances recall and ranking, for model selection.

**Pitfalls**

- Hard to explain to non-specialists; report `recall@k` and `mrr` alongside it.
- Binary relevance only; graded gains are reduced to relevant/not relevant. Use `ndcg` for graded labels.
- Unretrieved relevant ids count as 0, so a short ranking (or a small k) caps AP at retrieved-relevant ÷ relevant.
- Different from `context_precision`, which divides by the relevant items that were retrieved, not all relevant items.

**Example** (checked by the test suite against the real metric)

```jsonl
{"retrieved_ids": ["d3", "d1", "d7", "d2", "d9"], "relevant_ids": ["d1", "d2", "d5"]}
```

Result: **0.3333**. Relevant ids at ranks 2 and 4 give precisions 1/2 and 2/4; d5 is never retrieved, so AP = (0.5 + 0.5) / 3.

**Related:** [`mrr`](#mrr), [`ndcg`](#ndcg), [`r_precision`](#r_precision), [`context_precision`](rag.md#context_precision)

**References**

- Manning, C. D., Raghavan, P., and Schütze, H. (2008). Introduction to Information Retrieval, chapter 8: Evaluation in information retrieval. Cambridge University Press. <https://doi.org/10.1017/CBO9780511809071>

## hit_rate

*1 when at least one relevant id appears in the top k retrieved, else 0; the mean over samples is the share of queries with a hit (success@k).*

**Level:** sample · **Range:** 0 to 1, higher is better · **Needs:** `retrieved_ids`, `relevant_ids` or `relevance` · **Deterministic:** yes

**What it measures**

Whether retrieval found anything useful at all. It answers "for what share of questions does the top k contain at least one relevant item?" It suits datasets where each question has a single relevant document.

**How it is computed**

1. The relevant set is `relevant_ids`; if that is empty, every id in `relevance` with a gain above 0.
2. Cut the ranking to its first k ids (`k: 0` keeps all of it).
3. Score 1 if any id in the cut is relevant, otherwise 0. A sample with no relevant ids is skipped.
4. The run value is the mean over samples.

```text
hit_rate@k = 1 if relevant ∩ retrieved[1..k] ≠ ∅ else 0
```

**Inputs:** `retrieved_ids` (best first) and `relevant_ids` or `relevance`.

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `k` | `10` | Cut-off rank (default 10). `hit_rate@3` sets `k: 3`; `k: 0` means the whole ranking. |

**How to read it**

Per sample 0 or 1; the run mean is a share of queries, higher is better. With one relevant document per query it equals recall@k. It is coarse: it does not distinguish rank 1 from rank k, or one hit from five.

**Use it when**

- Single-answer retrieval (FAQ lookup, entity linking, one gold passage per question).
- A simple, explainable headline number ("the right passage is in the top 5 for 92% of questions").

**Pitfalls**

- Ignores position within the top k; pair with `mrr`.
- Ignores how many relevant items were found; for multi-document questions use `recall@k`.

**Example** (checked by the test suite against the real metric)

```jsonl
{"retrieved_ids": ["d3", "d1", "d7", "d2", "d9"], "relevant_ids": ["d1", "d2", "d5"]}
```

```yaml
metrics:
- name: hit_rate
  params:
    k: 5
```

Result: **1**. d1 at rank 2 is enough for a hit.

**Related:** [`recall`](#recall), [`mrr`](#mrr), [`precision`](#precision)

**References**

- Manning, C. D., Raghavan, P., and Schütze, H. (2008). Introduction to Information Retrieval, chapter 8: Evaluation in information retrieval. Cambridge University Press. <https://doi.org/10.1017/CBO9780511809071>

## mrr

*The reciprocal of the rank of the first relevant id (1 at rank 1, 0.5 at rank 2, 0 if none); the mean over samples is mean reciprocal rank.*

**Level:** sample · **Range:** 0 to 1, higher is better · **Needs:** `retrieved_ids`, `relevant_ids` or `relevance` · **Deterministic:** yes

**What it measures**

How early the first useful result appears. It answers "how far down does the user (or model) have to look before finding something relevant?" It was introduced for question answering, where one correct answer near the top is what matters.

**How it is computed**

1. The relevant set is `relevant_ids`; if that is empty, every id in `relevance` with a gain above 0.
2. Walk the ranking (cut to k when `k > 0`; by default the whole ranking).
3. Return 1 / rank of the first relevant id, or 0 if none is found. A sample with no relevant ids is skipped.
4. The run value is the mean over samples, which is MRR.

```text
RR  = 1 / min{ i : retrieved[i] ∈ relevant }      (0 if no relevant id in the cut)
MRR = (1/|Q|) Σ_q RR_q
```

**Inputs:** `retrieved_ids` (best first) and `relevant_ids` or `relevance`.

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `k` | `0` | Cut-off rank (default 0 = the whole ranking, unlike most retrieval metrics here). `mrr@10` sets `k: 10`, giving MRR@10, where a first hit below rank 10 counts as 0. |

**How to read it**

0–1, higher is better. 1.0 means the first result is always relevant; 0.5 corresponds to a typical first hit at rank 2. Because 1/rank falls quickly, MRR is dominated by the top few positions: moving a hit from rank 1 to 2 costs 0.5, from 9 to 10 only 0.011.

**Use it when**

- Single-answer search and QA retrieval, where only the first relevant result matters.
- Comparing rerankers, whose job is to move the best item to the top.

**Pitfalls**

- Only the first relevant id counts; the rest of the ranking is ignored. Use `average_precision` or `ndcg` for multi-relevant queries.
- {'The default `k': "0` differs from the other metrics' default of 10; state k when comparing with published MRR@10 numbers."}
- Its scale is non-linear, so differences between MRR values are not proportional to differences in rank.

**Example** (checked by the test suite against the real metric)

```jsonl
{"retrieved_ids": ["d3", "d1", "d7", "d2", "d9"], "relevant_ids": ["d1", "d2", "d5"]}
```

Result: **0.5**. The first relevant id (d1) is at rank 2.

**Related:** [`hit_rate`](#hit_rate), [`average_precision`](#average_precision), [`ndcg`](#ndcg)

**References**

- Voorhees, E. M. (1999). The TREC-8 Question Answering Track Report. Proceedings of the Eighth Text REtrieval Conference (TREC-8), NIST Special Publication 500-246, pp. 77–82. <https://trec.nist.gov/pubs/trec8/papers/qa_report.pdf>

## ndcg

*Normalised discounted cumulative gain at k, which rewards putting the most relevant ids first, on a 0–1 scale where 1 is the ideal ordering.*

**Level:** sample · **Range:** 0 to 1, higher is better · **Needs:** `retrieved_ids`, `relevant_ids` or `relevance` · **Deterministic:** yes

**What it measures**

Ranking quality with graded relevance. It answers "how close is this top-k ranking to the best possible ordering, given that some documents are more useful than others and lower positions are seen less?"

**How it is computed**

1. Gains come from `relevance` (id → graded gain, e.g. 0–3) when present, otherwise each id in `relevant_ids`
   has gain 1. A sample with no positive gain is skipped.
2. DCG: sum the gains of the retrieved ids in the top k, each divided by log2(rank + 1). Unlabelled ids have
   gain 0. With `exponential: true`, a gain g contributes 2^g − 1 instead of g.
3. IDCG: the same sum over the labelled gains sorted from highest to lowest and cut to k, i.e. the best ranking
   possible.
4. nDCG = DCG ÷ IDCG. The run value is the mean over samples.

```text
gain(g)  = g                 (linear, default)
         = 2^g − 1           (exponential: true)
DCG@k    = Σ_{i=1..k} gain(rel(retrieved[i])) / log2(i + 1)
IDCG@k   = Σ_{i=1..k} gain(g_(i)) / log2(i + 1)        g_(1) ≥ g_(2) ≥ … the labelled gains, sorted
nDCG@k   = DCG@k / IDCG@k
```

**Inputs:** `retrieved_ids` (best first) and `relevance` (graded: id → gain) or `relevant_ids` (binary: gain 1). When both are present, `relevance` is used.

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `k` | `10` | Cut-off rank (default 10). `ndcg@5` sets `k: 5`; `k: 0` uses the whole ranking and all labelled gains. |
| `exponential` | `False` | Use exponential gain 2^g − 1 instead of linear g (default false). Exponential gain strongly favours placing the highest-graded documents first; it matters only with graded `relevance`. |

**How to read it**

0–1, higher is better. 1.0 means the top k is ordered exactly as the ideal ranking. Linear and exponential gains give different numbers for the same ranking, so state which you used. Binary-label nDCG behaves like a position-discounted recall.

**Use it when**

- Graded relevance labels (perfect / good / fair), as in web search and product search.
- Evaluating rerankers, where both what is retrieved and its order matter.

**Pitfalls**

- Values depend on the gain scale and on linear vs exponential gain; never compare across labelling schemes.
- IDCG is built only from labelled documents, so incomplete labels can make a ranking look better than ideal-relative reality.
- {'The log discount is gentle': 'positions 9 and 10 still contribute; nDCG@k with large k mostly reflects recall.'}

**Example** (checked by the test suite against the real metric)

```jsonl
{"retrieved_ids": ["d3", "d1", "d7", "d2"], "relevance": {"d1": 3, "d2": 2, "d5": 1}}
```

```yaml
metrics:
- name: ndcg
  params:
    k: 4
```

Result: **0.5784**. DCG = 3/log2(3) + 2/log2(5) = 2.754; the ideal order (3, 2, 1) gives IDCG = 3 + 2/log2(3) + 1/2 = 4.762.

**Related:** [`average_precision`](#average_precision), [`mrr`](#mrr), [`recall`](#recall), [`context_precision`](rag.md#context_precision)

**References**

- Järvelin, K., and Kekäläinen, J. (2002). Cumulated Gain-Based Evaluation of IR Techniques. ACM Transactions on Information Systems 20(4), pp. 422–446. <https://doi.org/10.1145/582415.582418>
- Manning, C. D., Raghavan, P., and Schütze, H. (2008). Introduction to Information Retrieval, chapter 8: Evaluation in information retrieval. Cambridge University Press. <https://doi.org/10.1017/CBO9780511809071>

## precision

*The share of the top k retrieved ids that are relevant (precision@k).*

**Level:** sample · **Range:** 0 to 1, higher is better · **Needs:** `retrieved_ids`, `relevant_ids` or `relevance` · **Deterministic:** yes

**What it measures**

How clean the top of a ranking is. It answers "of the k results we show (or send to the model), how many are relevant?" It ignores order within the top k and ignores relevant items that were not retrieved.

**How it is computed**

1. The relevant set is `relevant_ids`; if that is empty, it is every id in `relevance` with a gain above 0.
2. Cut the ranking (`retrieved_ids`, best first) to its first k ids (`k: 0` keeps the whole ranking).
3. Count the relevant ids in the cut and divide by **k**, not by the number actually retrieved. A system that
   returns 3 ids, all relevant, scores 0.3 at k = 10. With `k: 0` the denominator is the ranking's length.
4. A sample with no relevant ids is skipped, as in every ranking metric. The run value is the mean over samples.

```text
precision@k = |{d ∈ retrieved[1..k] : d ∈ relevant}| / k          (k = len(retrieved) when k = 0)
```

**Inputs:** `retrieved_ids` (the ranking, best first) and `relevant_ids` (binary labels) or `relevance` (id → graded gain; any gain > 0 counts as relevant).

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `k` | `10` | Cut-off rank (default 10). Set it in the name: `precision@5` is `precision` with `k: 5`. `k: 0` means the whole ranking. |

**How to read it**

0–1, higher is better. Its maximum is |relevant| / k, so with one relevant document per query precision@10 can never exceed 0.1. Compare it only across systems with the same k and the same labels; for single-answer queries prefer `hit_rate@k` or `mrr`.

**Use it when**

- Result lists shown to people, where every irrelevant result in the first k costs attention.
- RAG pipelines with a fixed context budget of k chunks, where irrelevant chunks are noise for the generator.

**Pitfalls**

- Bounded by the number of relevant ids; low values on single-answer datasets are expected, not a failure.
- Dividing by k penalises returning fewer than k results, which is the standard definition but surprises people who expect "precision of what was returned".
- Unlabelled documents count as irrelevant, so incomplete labels understate precision.

**Example** (checked by the test suite against the real metric)

```jsonl
{"retrieved_ids": ["d3", "d1", "d7", "d2", "d9"], "relevant_ids": ["d1", "d2", "d5"]}
```

```yaml
metrics:
- name: precision
  params:
    k: 5
```

Result: **0.4**. Two of the top five (d1, d2) are relevant.

**Related:** [`recall`](#recall), [`hit_rate`](#hit_rate), [`r_precision`](#r_precision), [`average_precision`](#average_precision), [`context_precision`](rag.md#context_precision)

**References**

- Manning, C. D., Raghavan, P., and Schütze, H. (2008). Introduction to Information Retrieval, chapter 8: Evaluation in information retrieval. Cambridge University Press. <https://doi.org/10.1017/CBO9780511809071>

## r_precision

*Precision at rank R, where R is the number of relevant ids for the query, so the cut-off adapts to each query.*

**Level:** sample · **Range:** 0 to 1, higher is better · **Needs:** `retrieved_ids`, `relevant_ids` or `relevance` · **Deterministic:** yes

**What it measures**

Ranking quality at the one cut-off where precision and recall are equal. It answers "if the system returned exactly as many results as there are relevant items, what share would be relevant?"

**How it is computed**

1. The relevant set is `relevant_ids`; if that is empty, every id in `relevance` with a gain above 0.
   A sample with no relevant ids is skipped.
2. Let R be the number of relevant ids. Take the first R retrieved ids.
3. Divide the number of relevant ids among them by R. (If fewer than R ids were retrieved, the missing
   positions count as misses.)
4. The run value is the mean over samples.

```text
R            = |relevant|
R-precision  = |relevant ∩ retrieved[1..R]| / R        (= recall@R = precision@R)
```

**Inputs:** `retrieved_ids` (best first) and `relevant_ids` or `relevance`.

**How to read it**

0–1, higher is better. 1.0 means the first R results are exactly the relevant set. It has no k: the cut-off is set per query by R, which makes it comparable across queries with very different numbers of relevant items. It correlates closely with average precision.

**Use it when**

- Datasets where the number of relevant items varies a lot between queries.
- A single, easy-to-explain alternative to MAP.

**Pitfalls**

- It takes no `k`, so `r_precision@5` is rejected; it always cuts at R.
- Order within the first R does not matter.
- With R = 1 it reduces to "is the first result relevant?", which is very coarse.

**Example** (checked by the test suite against the real metric)

```jsonl
{"retrieved_ids": ["d3", "d1", "d7", "d2", "d9"], "relevant_ids": ["d1", "d2", "d5"]}
```

Result: **0.3333**. R = 3; of the first three retrieved (d3, d1, d7) only d1 is relevant.

**Related:** [`precision`](#precision), [`recall`](#recall), [`average_precision`](#average_precision)

**References**

- Manning, C. D., Raghavan, P., and Schütze, H. (2008). Introduction to Information Retrieval, chapter 8: Evaluation in information retrieval. Cambridge University Press. <https://doi.org/10.1017/CBO9780511809071>

## recall

*The share of the relevant ids that appear in the top k retrieved (recall@k).*

**Level:** sample · **Range:** 0 to 1, higher is better · **Needs:** `retrieved_ids`, `relevant_ids` or `relevance` · **Deterministic:** yes

**What it measures**

Coverage of retrieval. It answers "of everything relevant, how much made it into the top k?" For RAG this is usually the first number to watch: the generator cannot use a passage that was never retrieved.

**How it is computed**

1. The relevant set is `relevant_ids`; if that is empty, every id in `relevance` with a gain above 0.
2. Cut the ranking to its first k ids (`k: 0` keeps all of it).
3. Divide the number of relevant ids in the cut by the total number of relevant ids.
4. A sample with no relevant ids is skipped. The run value is the mean over samples.

```text
recall@k = |relevant ∩ retrieved[1..k]| / |relevant|
```

**Inputs:** `retrieved_ids` (best first) and `relevant_ids` or `relevance` (any gain > 0 counts as relevant).

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `k` | `10` | Cut-off rank (default 10). `recall@5` sets `k: 5`; `k: 0` means the whole ranking. |

**How to read it**

0–1, higher is better. 1.0 means everything relevant is within the top k. It rises with k, so always report k. For RAG, recall@k at the k you actually send to the model is the ceiling on what the generator can know; values above about 0.9 are a common target for single-hop questions.

**Use it when**

- Choosing k or comparing retrievers and embedding models for a RAG system.
- Any task where missing a relevant item is worse than showing an extra irrelevant one.

**Pitfalls**

- Trivially maximised by retrieving more; pair it with `precision@k` or `ndcg@k`.
- Order within the top k does not matter; use `mrr` or `ndcg` when position matters.
- {'Depends on label completeness': 'relevant documents nobody labelled are invisible, which inflates recall.'}

**Example** (checked by the test suite against the real metric)

```jsonl
{"retrieved_ids": ["d3", "d1", "d7", "d2", "d9"], "relevant_ids": ["d1", "d2", "d5"]}
```

```yaml
metrics:
- name: recall
  params:
    k: 5
```

Result: **0.6667**. d1 and d2 are found in the top five; d5 is not retrieved.

**Related:** [`precision`](#precision), [`hit_rate`](#hit_rate), [`ndcg`](#ndcg), [`context_recall`](rag.md#context_recall)

**References**

- Manning, C. D., Raghavan, P., and Schütze, H. (2008). Introduction to Information Retrieval, chapter 8: Evaluation in information retrieval. Cambridge University Press. <https://doi.org/10.1017/CBO9780511809071>
