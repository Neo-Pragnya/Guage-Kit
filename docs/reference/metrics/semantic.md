---
title: Semantic similarity metrics
description: "Embedding similarity and BERTScore-style token matching."
---

# Semantic similarity metrics

> [!NOTE]
> Generated from the metric registry and the metric cards (`guage_kit/metrics/cards/`). Every example
> on this page is run by the test suite, so the numbers are what the metric really returns.

Embedding similarity and BERTScore-style token matching.

| metric | in one line |
| --- | --- |
| [`bertscore`](#bertscore) | F1 of greedy token-to-token matching between output and reference by embedding cosine similarity (BERTScore without idf weighting or baseline rescaling). |
| [`semantic_similarity`](#semantic_similarity) | Cosine similarity between the embedding of the output and the embedding of the closest reference. |

## bertscore

*F1 of greedy token-to-token matching between output and reference by embedding cosine similarity (BERTScore without idf weighting or baseline rescaling).*

**Level:** sample · **Range:** 0 to 1, higher is better · **Needs:** `output`, `expected`, an embedder · **Deterministic:** yes · **Extra:** `pip install 'guage-kit[embeddings]'`

**What it measures**

Token-level semantic overlap. It answers "can each word of the output be matched to a similar word in the reference, and vice versa?" Unlike a single-vector similarity, it keeps track of which parts of each text are covered.

**How it is computed**

For each reference:
1. Get token embeddings for the output and the reference.
   - With an embedder that offers `token_embed` (a sentence-transformers model): the model's contextual token
     embeddings, as returned by the model (any special tokens it adds are included).
   - Otherwise (the built-in hashing embedder): split both texts into words and embed each word on its own,
     so vectors are per word and not contextual.
2. Recall: for each reference token, the highest cosine with any output token; averaged.
   Precision: for each output token, the highest cosine with any reference token; averaged.
3. F1 of the two.
The score is the F1 of the reference with the highest F1 (precision and recall of that reference are in the
details). If either text has no tokens, the score is 0.

Differences from Zhang et al.: no inverse-document-frequency weighting, no baseline rescaling, and the
embeddings come from the configured sentence-transformers model's output layer rather than a chosen layer of a
model selected for the metric. Numbers are therefore not comparable with published BERTScore values.

```text
R_bert = (1/|ref|)  Σ_{x ∈ ref}  max_{y ∈ out} cos(x, y)
P_bert = (1/|out|)  Σ_{y ∈ out}  max_{x ∈ ref} cos(x, y)
F_bert = 2 · P_bert · R_bert / (P_bert + R_bert)
bertscore = F_bert of the best-matching reference
```

**Inputs:** `output` and `expected` (or `references`; the best reference by F1 counts).

**How to read it**

0–1 in practice, higher is better. Without baseline rescaling, contextual embeddings give high values even for unrelated sentences (often 0.7 and up with transformer models), so the useful range is compressed near the top: differences of a few hundredths can matter. With the hashing fallback the metric behaves like a soft word overlap F1. Compare systems on the same data and embedder only.

**Use it when**

- Summarisation, captioning and paraphrase tasks, where word choice varies but content should match.
- When you want to see whether a low score comes from missing content (low recall) or extra content (low precision).

**Pitfalls**

- Without `guage-kit[embeddings]` and a sentence-transformers model it falls back to hashed word vectors, which measure spelling similarity, not meaning.
- Not comparable with the original BERTScore numbers (no idf, no rescaling, different model and layer).
- Like other embedding metrics it is weak on negation and numbers.
- Slower than sentence-level similarity, because every token pair is compared.

**Example** (checked by the test suite against the real metric)

```jsonl
{"output": "The cat sat on the mat.", "expected": "A cat was sitting on the mat."}
```

Result: **0.6857**. Computed with the built-in hashing embedder (word-level fallback; precision 0.857, recall 0.571). A real embedding model gives a different value.

**Related:** [`semantic_similarity`](#semantic_similarity), [`rouge`](text.md#rouge), [`bleu`](text.md#bleu), [`answer_correctness`](rag.md#answer_correctness)

**References**

- Zhang, T., Kishore, V., Wu, F., Weinberger, K. Q., and Artzi, Y. (2020). BERTScore: Evaluating Text Generation with BERT. Proceedings of ICLR 2020. <https://arxiv.org/abs/1904.09675>

## semantic_similarity

*Cosine similarity between the embedding of the output and the embedding of the closest reference.*

**Level:** sample · **Range:** 0 to 1, higher is better · **Needs:** `output`, `expected`, an embedder · **Deterministic:** yes

**What it measures**

Closeness in meaning between generated text and a reference, independent of exact wording (to the extent the embedder captures meaning). It answers "does the output say roughly the same thing as the reference?"

**How it is computed**

1. Embed the output and every reference with the run's embedder. With none configured, the built-in
   `HashingEmbedder` is used: hashed word and character 3–5-gram features, sublinear term frequency,
   L2-normalised. It is offline and deterministic but lexical, not semantic.
2. Compute the cosine similarity between the output vector and each reference vector.
3. Keep the highest, floored at 0. The details record which embedder was used.

The approach follows the sentence-embedding similarity of Sentence-BERT: one vector per text, compared by
cosine. Configure a sentence-transformers model (`embedder:` in guage.yaml, `pip install guage-kit[embeddings]`)
to get real semantic similarity.

```text
semantic_similarity = max(0, max_r cos(embed(output), embed(reference_r)))
cos(a, b) = (a · b) / (‖a‖ ‖b‖)
```

**Inputs:** `output` and `expected` (or `references`; the closest reference counts).

**How to read it**

0–1, higher is better. The scale depends entirely on the embedder: unrelated sentences often score 0.1–0.3 with sentence-transformer models and near 0 with the hashing embedder, while paraphrases typically score above 0.7 with a good model. Calibrate a pass threshold on a few labelled pairs for your embedder, and never compare values produced by different embedders.

**Use it when**

- Free-form answers where many phrasings are correct and n-gram metrics such as `bleu` are too strict.
- Regression testing that outputs keep their meaning across prompt or model changes.

**Pitfalls**

- With the default hashing embedder it measures character and word overlap, not meaning; paraphrases with different words score low.
- Embeddings are poor at negation, numbers and small factual changes ("refundable in 14 days" vs "in 30 days" stays very similar). Use `answer_correctness` or a judge for facts.
- Long texts are compressed into one vector, so a missing detail barely moves the score.
- Values are not comparable across embedders, model versions or languages.

**Example** (checked by the test suite against the real metric)

```jsonl
{"output": "The cat sat on the mat.", "expected": "A cat was sitting on the mat."}
```

Result: **0.5385**. Computed with the built-in hashing embedder (what the test context and an unconfigured run use). A real embedding model gives a different, typically higher, value for this paraphrase.

**Related:** [`bertscore`](#bertscore), [`answer_relevancy`](rag.md#answer_relevancy), [`answer_correctness`](rag.md#answer_correctness), [`bleu`](text.md#bleu)

**References**

- Reimers, N., and Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks. Proceedings of EMNLP-IJCNLP 2019, pp. 3982–3992. <https://arxiv.org/abs/1908.10084>
