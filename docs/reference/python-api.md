---
title: Python API
description: The guage_kit package's public functions and classes, with their signatures.
---

# Python API

> [!TIP]
> This page is a guided tour. The [API reference](api.md) documents every public class and function, with
> signatures and fields generated from the code.

```python
import guage_kit as gk
```

The top-level package exports: `evaluate`, `compare`, `report`, `list_metrics`, `load_dataset`, `metric`,
`corpus_metric`, `Sample`, `ToolCall`, `Usage`, `Dataset`, `RunResult`, `SampleResult`, `Score`, `MetricSummary`,
`GateRule`, `GateResult`, `MetricContext`, `GuageError` and `__version__`. Everything else is importable from its
module, listed below.

## Running evaluations

### `gk.evaluate`

```python
evaluate(
    data,                      # Dataset | list[Sample | dict] | path to a dataset file
    metrics=None,              # list of names/specs, a comma-separated string, None or "auto"
    *,
    target=None,               # callable | "module:function" | provider spec | Target
    judge=None,                # "heuristic" | provider spec | judge object | provider object
    embedder=None,             # "hashing" | model name | embedder object
    gates=None,                # list of GateRule or dicts {"metric", "min", "max", "on_fail"}
    slices=None,               # ["tags", "<metadata key>", ...]
    name="",                   # run name (default: the dataset name)
    concurrency=4,             # parallel target calls and judged metrics
    repeats=1,                 # target calls per sample; >1 adds self_consistency
    confidence=0.95,           # interval level
    n_resamples=1000,          # bootstrap resamples
    seed=0,
    save=False,                # True: .guage/runs/<id>/run.json under project_root; or a directory
    evidence=False,            # also write an Ananke evidence bundle
    project_root=".",
    progress=None,             # callable(stage, done, total)
    config=None,               # extra dict recorded in run.config
) -> RunResult
```

A metric spec is a name (`"recall@5"`) or a dict `{"name", "params", "threshold", "as"}`. See [Metrics](../guides/metrics.md).
`guage_kit.runner.auto_metrics(samples)` returns what `None` would choose.

### `gk.compare`

```python
compare(a, b, *, metrics=None, alpha=0.05, min_effect=0.0, n_resamples=2000, seed=0, top=10) -> Comparison
```

`a` is the baseline, `b` the candidate: `RunResult`s, run ids or paths (resolved in `./.guage/runs`). Returns a
`guage_kit.runner.compare.Comparison` with `metrics` (`MetricDelta` per metric: `a`, `b`, `delta`, `ci_low`,
`ci_high`, `p_value`, `p_adjusted`, `effect_size`, `wins`, `losses`, `ties`, `n`, `direction`), `regressions` and
`improvements` (`SampleDelta` lists), `same_data`, `common_samples`, and the properties `improved` and `regressed`
(metric names). See [Statistics](../guides/statistics.md).

`guage_kit.runner.pairwise(a, b, judge, *, criterion="helpfulness", limit=None, seed=0) -> dict` judges outputs
head to head in both orders. `guage_kit.runner.regression_gate(comparison, rules) -> list[str]` lists `max_drop`
violations.

### `gk.report`

```python
report(result, path, *, comparison=None, profile="private", title=None, run_b=None) -> Path
```

Writes the HTML report. `result` is a `RunResult` (optionally with a `comparison`), or a `Comparison` together with
`run_b`, the candidate run. `guage_kit.reports` also has `markdown(run, comparison=None)`, `junit(run)` and
`write_all(run, out_dir, *, comparison=None, profile="private")`.

### Suites

```python
from guage_kit.config import load_suite, run_suite
suite = load_suite("guage.yaml")              # Suite (pydantic); raises GK-CONFIG-001 on errors
run, comparison = run_suite(suite, overrides={"save": True, "baseline": "baseline:main"})
```

`overrides` accepts `judge`, `target`, `save` and `baseline`. See [Configuration](configuration.md).

### Run storage

```python
from guage_kit.runner import RunStore, load_run
store = RunStore(".guage/runs")
store.save(run); store.list(); store.load("latest"); store.load("baseline:main")
store.set_baseline("latest", "main")          # -> .guage/baselines/main.json
load_run("latest")                            # a RunResult, run id or path
```

## Data

### `gk.Sample`

A pydantic model with the fields in [Datasets](../guides/datasets.md#sample-fields), and the views `output_text`,
`input_text`, `expected_texts`, `predicted_label` and `has(field)`. Unknown fields are rejected when you construct a
`Sample` directly (the dataset loader moves them to `metadata`).

`gk.ToolCall(name, arguments={}, output=None, error=None)` and
`gk.Usage(prompt_tokens=None, completion_tokens=None, total_tokens=None, cost_usd=None)` (with `.tokens`).

### `gk.Dataset`

```python
Dataset(samples, *, name="dataset", source="")
Dataset.load(path, *, name=None)              # also gk.load_dataset(path)
Dataset.from_records(records, *, name="dataset", source="")
ds.fingerprint, ds.input_fingerprint
ds.filter(predicate, *, name=None); ds.with_tag(tag); ds.sample(n, *, seed=0)
ds.split(fraction, *, seed=0) -> (Dataset, Dataset); ds.map(fn)
ds.get(id); ds.save(path); ds.to_records(); ds.stats()
len(ds); ds[0]; iter(ds)
```

## Results

| Class | Key fields |
| --- | --- |
| `RunResult` | `run_id`, `name`, `created_at`, `duration_s`, `dataset`, `target`, `metrics`, `config`, `samples`, `summaries`, `slices`, `gate`, `judge`, `environment`, `notes`; methods `value(metric)`, `scores(metric)`, `table()`, `to_json()`, `save(path)`, `RunResult.load(path)` |
| `SampleResult` | `sample_id`, `input`, `output`, `expected`, `tags`, `scores`, `target_error`, `latency_ms`, `repeats`; property `failed_metrics` |
| `Score` | `metric`, `value`, `passed`, `skipped`, `error`, `reason`, `details` |
| `MetricSummary` | `metric`, `family`, `description`, `higher_is_better`, `level`, `n`, `skipped`, `errors`, `value`, `mean`, `median`, `std`, `min`, `max`, `ci_low`, `ci_high`, `threshold`, `pass_rate`, `histogram`, `histogram_range`, `details` |
| `GateRule` | `metric`, `min`, `max`, `on_fail` (`block`/`warn`/`review`), `max_drop` |
| `GateResult` | `verdict`, `checks` (`GateCheck`: `metric`, `value`, `rule`, `ok`, `message`), `evidence`, `decided_by`; property `blocks` |

The JSON shape is in [Report and run formats](report-format.md).

## Metrics

```python
@gk.metric(name, *, family, description="", requires=(), requires_any=(), higher_is_better=True,
           value_range=(0.0, 1.0), deterministic=True, needs_judge=False, needs_embedder=False,
           extra=None, reference="", registry=None, replace=False)
@gk.corpus_metric(...)          # same options
gk.list_metrics(family=None) -> list[dict]
```

From `guage_kit.metrics.registry`: `get_metric(name) -> MetricInfo`, `resolve(spec) -> BoundMetric` (with
`.score(sample, ctx)` and `.compute(samples, ctx)`), `MetricContext(judge=None, embedder=None, seed=0, options={})`,
`CorpusOutput(value, details={}, per_sample={})`, and `REGISTRY`.

## Judges

From `guage_kit.judges`:

```python
make_judge(spec, **options) -> BaseJudge | None      # "heuristic" or a provider spec/object
LLMJudge(provider, *, samples=1, cache_dir=".guage/cache/judge", provider_options=None)
HeuristicJudge()
judge.grade(sample, criterion) -> Verdict            # score (0-1), raw_score, reason, samples, cached
judge.entailment(premise=..., hypothesis=...) -> float
judge.pairwise(question=..., a=..., b=..., criterion="helpfulness", reference=None) -> PairwiseVerdict
judge.usage, judge.describe()
make_provider(spec, **options) -> Provider            # AnthropicProvider, OpenAICompatibleProvider, CallableProvider, ...
AnthropicProvider(model="claude-opus-5-5", *, max_tokens=16000, effort=None, fallbacks=True, client=None)
CallableProvider(fn, name="python")                  # fn(system, prompt) -> str | dict | Completion
CRITERIA, Criterion, get_criterion(spec)
agreement(judge_scores, human_scores) -> dict; weighted_kappa(a, b, *, weights="quadratic"); position_consistency(verdicts)
```

`BedrockProvider` and `Completion` are in `guage_kit.judges.providers`.

## Targets

From `guage_kit.runner`: `Target(fn, *, name=None, retries=0, backoff_s=1.0)`,
`ProviderTarget(provider, *, system="You are a helpful assistant.", template="{input}", retries=2)` and
`make_target(spec, **options)`.

## Embedders

From `guage_kit.metrics.semantic`: `HashingEmbedder(dim=1024)`,
`SentenceTransformerEmbedder(model="sentence-transformers/all-MiniLM-L6-v2", device=None)`,
`make_embedder(spec)` and `cosine(a, b)`.

## Statistics, probes, synthetic data

- `guage_kit.stats`: see [Statistics](../guides/statistics.md#the-functions).
- `guage_kit.probes`: `perturb(dataset, kinds, *, seed=0)`, `robustness(dataset, target, *, kinds, metrics=None, seed=0, concurrency=4)`,
  `redteam_dataset(*, system_prompt=None, benign_context=..., seed=0)`, `canary()`, `PERTURBATIONS`.
- `guage_kit.synth`: `read_documents(paths)`, `chunk(documents, *, size=120, overlap=20)`,
  `cloze_dataset(chunks, *, per_chunk=1, seed=0, name="synthetic-cloze")`,
  `generate_qa(chunks, provider, *, per_chunk=2, name="synthetic-qa")`, `write_corpus(chunks, path)`.

## Ananke bridge

`guage_kit.harness.negotiation`: `SUPPORTED_ANANKE`, `check()`, `installed_version()`, `supported(version)`, `probe()`.
`guage_kit.harness.catalogue`: `discover()`, `run_evaluator(id, sample, config=None, project_root=None)`, `register_all()`.
`guage_kit.harness.convert`: `to_case`, `to_trace`, `tool_calls_from_trace`, `to_scores`, `to_policy`, `gate`,
`to_report`, `write_evidence(run, project_root=".", rules=None)`. See [Ananke integration](../concepts/ananke-integration.md).

## Errors

`gk.GuageError` has `code`, `message` and `hint`. The codes are in [Error codes](errors.md).
