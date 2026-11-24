---
title: Datasets
description: The sample model, accepted field names and file formats, fingerprints, dataset tools and automatic metric selection.
---

# Datasets

A dataset is an ordered list of samples with unique ids. A sample holds whatever the metrics need. Every field except
`id` is optional, and each metric declares which fields it requires. A sample without them is **skipped with a
reason**, never scored as zero.

## Sample fields

| Field | Type | Used by |
| --- | --- | --- |
| `id` | string (numbers are converted) | everything; must be unique |
| `input` | any (text, chat messages, dict) | targets, judges, relevancy metrics |
| `output` | any | almost every metric; filled in by a [target](targets.md) when missing |
| `expected` | any (text, label, number, JSON) | reference-based metrics, classification gold label, STS gold score |
| `references` | list of strings | extra acceptable answers (metrics take the best match) |
| `contexts` | list of strings | RAG metrics: the retrieved passages, in rank order |
| `retrieved_ids` | list of strings | retrieval metrics: the ranking, best first |
| `relevant_ids` | list of strings | retrieval metrics: binary relevance |
| `relevance` | map id → gain | graded relevance for nDCG |
| `label` | string | predicted class (otherwise taken from `probabilities` or a short `output`) |
| `probabilities` | map label → probability | classification and calibration |
| `confidence` | number | calibration (otherwise the top probability) |
| `embeddings` | map name → vector | embedding metrics (keys `a` and `b` for a pair) |
| `tool_calls` | list of `{name, arguments, output, error}` | agent metrics: what the agent did |
| `expected_tool_calls` | list of the same | agent metrics: what it should have done |
| `trace` | object | an agent trace that Ananke can normalise (spans of kind `tool`, `retrieval`, `model`, …) |
| `latency_ms` | number | runtime metrics; measured automatically when a target runs |
| `usage` | `{prompt_tokens, completion_tokens, total_tokens, cost_usd}` | token and cost metrics |
| `tags` | list of strings | slicing and filtering |
| `metadata` | map | anything else; some metrics read keys from it (`keywords`, `pattern`, `schema`, `should_refuse`, `canary`, `system_prompt`, `success`, `counterfactual_group`, `ananke`) |

`Sample.expected_texts` is `expected` (or each item of a list) followed by `references`: the list of acceptable
answers that text metrics compare against.

## Field names from other tools

Files often use other names. The loader maps these onto sample fields:

| In your file | Becomes |
| --- | --- |
| `question`, `query`, `prompt`, `user_input`, `messages` | `input` |
| `answer`, `response`, `prediction`, `completion`, `generated` | `output` |
| `ground_truth`, `reference`, `target`, `gold`, `ideal` | `expected` |
| `ground_truths` | `references` |
| `retrieved_contexts`, `context`, `documents` | `contexts` |
| `predicted_label` | `label` |
| `probs` | `probabilities` |
| `expected_tools` | `expected_tool_calls` |
| `tools` | `tool_calls` |

Any other key is kept in `metadata`, never dropped. If a file has both `answer` and `output`, the real field name wins
and the alias goes to `metadata`.

## File formats

| Extension | Shape |
| --- | --- |
| `.jsonl`, `.ndjson` | one JSON object per line (blank lines ignored; errors name the line number) |
| `.json` | a list of objects, or an object with a `samples`, `data`, `cases`, `examples` or `rows` list |
| `.yaml`, `.yml` | the same shapes as JSON |
| `.csv`, `.tsv` | one row per sample. Cells that start with `[` or `{` are parsed as JSON. List fields (`references`, `contexts`, `retrieved_ids`, `relevant_ids`, `tags`) also accept `a|b|c` |

```python
from guage_kit import Dataset, load_dataset

ds = load_dataset("data/qa.jsonl")        # same as Dataset.load(...)
ds = Dataset.from_records([{"question": "Q?", "answer": "A", "ground_truth": "A"}], name="inline")
ds.save("data/qa.yaml")                     # .jsonl, .json or .yaml
```

## Fingerprints

- `ds.fingerprint` is a SHA-256 over every sample's full content, outputs included. Equal data gives an equal
  fingerprint.
- `ds.input_fingerprint` covers only ids, inputs, `expected`, `references` and `relevant_ids`. Two runs of different
  systems on the same test set share it, which is how a comparison knows it is comparing like with like.

Both are recorded in every run (`run.dataset`).

## Working with datasets

```python
ds.filter(lambda s: "hard" in s.tags)
ds.with_tag("hard")
ds.sample(50, seed=0)          # reproducible random subset
dev, test = ds.split(0.3, seed=0)
ds.map(lambda s: s.model_copy(update={"output": None}))
ds.stats()                      # field coverage, tag counts, output lengths
ds.get("q17")
```

The same operations from the command line:

```bash
guage data validate data/qa.jsonl
guage data stats data/qa.jsonl            # coverage, tags and the metrics `auto` would pick
guage data convert data/qa.csv data/qa.jsonl
guage data split data/qa.jsonl --fraction 0.3 --seed 0   # writes qa.a.jsonl and qa.b.jsonl
guage data sample data/qa.jsonl -n 50 -o data/qa-50.jsonl
```

## Automatic metric selection

With `metrics: auto` (or `metrics=None` in Python), Guage Kit chooses metrics from the fields at least half the
samples have. Selection happens after the target runs, so outputs it produces count.

| When the data has | Metrics added |
| --- | --- |
| `label` or `probabilities`, and `expected` | `accuracy`, `f1`, `balanced_accuracy`, `cohen_kappa`; with probabilities or confidence also `ece`, `brier`, `selective_auroc` |
| `embeddings`, or numeric `expected` | `sts_spearman`, `sts_pearson` |
| `output` and short `expected` (4 words or fewer) | `normalized_match`, `contains`, `token_f1`, `semantic_similarity` |
| `output` and longer `expected` | `token_f1`, `rougeL`, `bleu`, `chrf`, `semantic_similarity` |
| numbers in every reference | `numeric_match` |
| `retrieved_ids` and relevance | `recall@5`, `precision@5`, `mrr`, `ndcg@10`, `hit_rate@5` |
| `contexts` | with `output`: `faithfulness`, `answer_relevancy`, `context_utilization`; with `expected`: `context_recall`, `context_precision`; with both: `answer_correctness` |
| `expected_tool_calls` and tool calls or a trace | `tool_call_f1`, `tool_args_accuracy`, `tool_sequence_match`, `tool_calls_exact` |
| tool calls or a trace | `tool_error_rate`, `redundant_tool_calls` |
| `metadata.should_refuse` / `canary` / `schema` / `success` / `counterfactual_group` on any sample | `refusal_correctness` / `injection_resistance` / `json_schema` / `goal_success` / `counterfactual_consistency` |
| `output` (not classification) | `pii_leakage`, `secret_leakage`, `toxicity` |
| `latency_ms` | `latency_p50`, `latency_p95` |
| `usage` | `total_tokens`; with costs also `cost_usd`, `total_cost_usd` |

Automatic selection is a starting point. For a release gate, list the metrics explicitly so the suite doesn't change
when the data does.
