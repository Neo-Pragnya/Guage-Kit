---
title: Metrics
description: Metric families, naming and parameters, thresholds, sample versus corpus metrics, skips and errors, and writing your own metrics.
---

# Metrics

Every metric is a plain function with a declaration: its family, the sample fields it needs, whether higher is
better, its range, and its configurable parameters. `guage metrics list` shows them all, `guage metrics show <name>`
shows one, and the [metric reference](../reference/metrics.md) documents every one in full: how it is computed, how to read it,
its pitfalls, a worked example and the papers behind it.

## Families

| Family | What it covers | Guide | Reference |
| --- | --- | --- | --- |
| `text` | matching, token F1, BLEU, chrF, ROUGE, edit distance, length, readability, diversity | this page | [text](../reference/metrics/text.md) |
| `semantic` | embedding similarity, BERTScore-style matching | [Embeddings](embeddings.md) | [semantic](../reference/metrics/semantic.md) |
| `rag` | faithfulness, hallucination rate, context precision, recall, relevance and utilisation, answer relevancy and correctness, citations | [RAG](rag.md) | [rag](../reference/metrics/rag.md) |
| `retrieval` | precision, recall, hit rate, MRR, MAP, nDCG, R-precision | [RAG](rag.md) | [retrieval](../reference/metrics/retrieval.md) |
| `classification`, `calibration` | accuracy, F1, kappa, MCC, ECE, Brier, selective AUROC | [Classification](classification-and-calibration.md) | [classification](../reference/metrics/classification.md), [calibration](../reference/metrics/calibration.md) |
| `embeddings` | STS correlation, alignment, uniformity, anisotropy | [Embeddings](embeddings.md) | [embeddings](../reference/metrics/embeddings.md) |
| `structured` | JSON and YAML validity, JSON Schema, field accuracy, Python syntax | this page | [structured](../reference/metrics/structured.md) |
| `agent` | tool-call F1, arguments, sequence, errors, redundancy, goal success | [Agents](agents.md) | [agent](../reference/metrics/agent.md) |
| `ananke.*` | 77 agent-trace evaluators from Ananke Plexus | [Agents](agents.md) | [ananke](../reference/metrics/ananke.md) |
| `safety` | refusal, PII, secrets, injection, system-prompt leakage, toxicity, counterfactual consistency | [Safety](safety-and-red-teaming.md) | [safety](../reference/metrics/safety.md) |
| `runtime` | latency, tokens, cost | this page | [runtime](../reference/metrics/runtime.md) |
| `judge` | an LLM judge's grade on a criterion | [Judges](judges.md) | [judge](../reference/metrics/judge.md) |

The text metrics are implemented in Guage Kit and tested against reference implementations: BLEU, chrF and chrF++
match sacreBLEU, and ROUGE matches rouge-score (ROUGE's `tokenizer="unicode"` keeps non-ASCII words, which the
reference tokeniser drops). Classification and ranking metrics are tested against scikit-learn.

## Naming a metric

A metric can be given as:

- a name: `"token_f1"`, `"rougeL"`;
- a name with `@k`, which sets the parameter `k`: `"recall@5"`, `"ndcg@10"`, `"latency_p95@99"`, `"distinct_n@1"`;
- a spec with parameters, a threshold and a display name:

```yaml
metrics:
  - token_f1
  - recall@5
  - {name: faithfulness, threshold: 0.8}
  - {name: rouge, params: {variant: rouge2}, as: rouge2_strict}
  - {name: judge, params: {criterion: correctness}, as: judge_correctness}
```

`as:` lets the same metric run more than once with different parameters. Two metrics may not share a display name.
Unknown parameters are rejected (`GK-METRIC-002`), and an unknown name suggests the closest one (`GK-METRIC-001`).

## Thresholds

A `threshold` marks each sample as passing or failing (respecting the metric's direction: for lower-is-better metrics
a value must be at or below it). The summary then has a `pass_rate`, and the report highlights failing samples.
A threshold is per sample. To fail a whole run, use a [gate](gates-and-ci.md).

## Sample and corpus metrics

Most metrics score each sample, and the run value is the mean, with a bootstrap confidence interval over samples.
**Corpus metrics** need all samples at once: `bleu`, `corpus_chrf`, `accuracy`, `f1`, `cohen_kappa`, `mcc`, `ece`,
`mce`, `selective_auroc`, `sts_spearman`, `distinct_n`, `self_bleu`, `latency_p50`, `latency_p95`,
`total_cost_usd` and a few more. Their confidence interval comes from recomputing the metric on resampled datasets.
Some corpus metrics (accuracy, counterfactual consistency) also report a per-sample value for the report.

## Skipped and errored

| Status | When | Effect |
| --- | --- | --- |
| skipped | the sample lacks a required field, or the metric does not apply (for example `json_schema` without a schema) | left out of the mean, counted in `skipped`, reason shown |
| error | the metric raised an exception | left out of the mean, counted in `errors`, message shown |

A metric that is skipped on every sample has no value. A gate on it never passes silently (see
[Gates](gates-and-ci.md#missing-values)).

## Runtime metrics

`latency_ms`, `total_tokens` and `cost_usd` are per sample. `latency_p50`, `latency_p95` (`@k` for other
percentiles) and `total_cost_usd` are per run. Cost comes from `usage.cost_usd`, or from token counts with a price
table you pass, because prices change and none ship with Guage Kit:

```yaml
metrics:
  - {name: cost_usd, params: {prices: {my-model: [0.25, 1.25]}}}   # dollars per million input, output tokens
```

The model name is read from `metadata.model`.

## Structured output

| Metric | Value |
| --- | --- |
| `json_valid` | 1 when the output contains valid JSON (fenced blocks and the first balanced object are found); `strict: true` requires the whole output to be JSON |
| `json_schema` | 1 when the JSON conforms to `params.schema` or `metadata.schema`; the details list the errors |
| `json_field_accuracy` | F1 over leaf fields of the expected JSON (strings compared case-insensitively, lists as sets) |
| `json_match` | 1 when the JSON equals the expected JSON |
| `yaml_valid` | 1 when the output parses to a mapping or list |
| `python_syntax` | 1 when the output (or its first ```` ```python ```` block) parses. Nothing is executed |

## Writing your own metric

```python
import guage_kit as gk
from guage_kit import Sample

@gk.metric("mentions_price", family="custom", requires=("output",))
def mentions_price(sample: Sample, *, currency: str = "$") -> float:
    """1 when the answer states a price."""
    return float(currency in sample.output_text)

@gk.corpus_metric("unique_answers", family="custom", requires=("output",))
def unique_answers(samples: list[Sample]) -> float:
    """Share of distinct outputs across the run."""
    return len({s.output_text for s in samples}) / len(samples)

data = [Sample(id="1", output="Pro costs $6 a month."), Sample(id="2", output="Pro costs $6 a month."),
        Sample(id="3", output="It is free.")]
run = gk.evaluate(data, ["mentions_price",
                         {"name": "mentions_price", "params": {"currency": "€"}, "as": "mentions_euro"},
                         "unique_answers"])
print({k: round(v.value, 3) for k, v in run.summaries.items()})
```

```text
{'mentions_price': 0.667, 'mentions_euro': 0.0, 'unique_answers': 0.667}
```

Rules:

- The first argument is the sample (or the list of samples for a corpus metric). Every other parameter needs a
  default, and those defaults become the configurable parameters.
- A parameter named `ctx` receives the `MetricContext` (`ctx.judge`, `ctx.embedder`, `ctx.seed`).
- Return a float, a `(float, details)` tuple, a `Score`, or `None` to skip the sample. `details` may include
  `"reason"`, which is shown in the report. A corpus metric may return a `CorpusOutput(value, details, per_sample)`.
- Declaration options: `family`, `description` (default: the docstring's first paragraph), `requires`,
  `requires_any`, `higher_is_better`, `value_range`, `deterministic`, `needs_judge`, `needs_embedder`, `extra`,
  `reference`, `replace` (to override an existing name).
- Exceptions inside a metric become per-sample errors. They do not stop the run.

### Sharing metrics as a package

Register metrics from another package through the `guage_kit.metrics` entry-point group. Guage Kit imports each
advertised module the first time a metric is looked up:

```toml
# your package's pyproject.toml
[project.entry-points."guage_kit.metrics"]
acme = "acme_metrics.guage"   # a module whose import runs @gk.metric decorators
```

A plugin that fails to import prints its traceback and is skipped. The built-in metrics keep working.
