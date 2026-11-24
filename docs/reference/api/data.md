---
title: "Samples, datasets and results"
description: "The data model: Sample, Dataset, and the run records (RunResult, Score, MetricSummary, gates)."
---

# Samples, datasets and results

> [!NOTE]
> Generated from the code by `scripts/gen_api_docs.py`; signatures and docstrings are the installed
> package's.

Every metric reads a `Sample`; every run produces a `RunResult` that is saved as `run.json` and rendered into reports.

## `guage_kit.core.sample`

The sample: one thing to evaluate.

A sample holds whatever the metrics need. Most fields are optional: a text metric reads `output` and `expected`,
a retrieval metric reads `retrieved_ids` and `relevant_ids`, an agent metric reads `tool_calls` or `trace`.
Each metric declares the fields it requires, and a sample without them is skipped with a reason, never scored as 0.

### `Sample`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/sample.py#L45)

One evaluation sample. Unknown fields in files are kept in `metadata` by the dataset loader.

| field | type | default |
| --- | --- | --- |
| `id` | `str` | required |
| `input` | `Any` | `''` |
| `output` | `Any` | `None` |
| `expected` | `Any` | `None` |
| `references` | `list[str]` | `[]` |
| `contexts` | `list[str]` | `[]` |
| `retrieved_ids` | `list[str]` | `[]` |
| `relevant_ids` | `list[str]` | `[]` |
| `relevance` | `dict[str, float]` | `{}` |
| `label` | `str \| None` | `None` |
| `probabilities` | `dict[str, float]` | `{}` |
| `confidence` | `float \| None` | `None` |
| `embeddings` | `dict[str, list[float]]` | `{}` |
| `tool_calls` | `list[ToolCall]` | `[]` |
| `expected_tool_calls` | `list[ToolCall]` | `[]` |
| `trace` | `dict[str, Any] \| None` | `None` |
| `latency_ms` | `float \| None` | `None` |
| `usage` | `Usage \| None` | `None` |
| `tags` | `list[str]` | `[]` |
| `metadata` | `dict[str, Any]` | `{}` |

- **`Sample.expected_texts`** *(property)*: Every acceptable reference answer: `expected` (when text) followed by `references`.
- **`Sample.has(field: str) -> bool`**  
  Whether the field a metric needs is present and non-empty.

### `ToolCall`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/sample.py#L15)

A tool (function) call an agent made, or one it was expected to make.

| field | type | default |
| --- | --- | --- |
| `name` | `str` | required |
| `arguments` | `dict[str, Any]` | `{}` |
| `output` | `Any` | `None` |
| `error` | `str \| None` | `None` |


### `Usage`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/sample.py#L26)

Token usage and cost for producing a sample's output.

| field | type | default |
| --- | --- | --- |
| `prompt_tokens` | `int \| None` | `None` |
| `completion_tokens` | `int \| None` | `None` |
| `total_tokens` | `int \| None` | `None` |
| `cost_usd` | `float \| None` | `None` |


## `guage_kit.core.dataset`

Datasets: load, validate, fingerprint, slice and save collections of samples.

Supported files: JSON Lines (`.jsonl`), JSON (a list, or an object with `samples`), CSV and YAML. Field names
from common tools are mapped to the sample model (`question` → `input`, `ground_truth` → `expected` …).
Anything unrecognised is kept in `metadata`, never dropped.

### `ALIASES`

```python
ALIASES = {'question': 'input', 'query': 'input', 'prompt': 'input', 'user_input': 'input', 'messages': 'input', 'answer': 'output', 'response': 'output', 'prediction': 'output', 'completion': 'output', 'generated': 'output', 'ground_truth': 'expected', 'reference': 'expected', 'target': 'expected', 'gold': ' …
```

### `Dataset`

```python
class Dataset(samples: Iterable[Sample], *, name: str = 'dataset', source: str = '') -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/dataset.py#L91)

An ordered collection of samples with a stable content fingerprint.

- **`Dataset.get(sample_id: str) -> Sample | None`**
- **`Dataset.fingerprint`** *(property)*: sha256 over the canonical JSON of every sample: equal data, equal fingerprint.
- **`Dataset.input_fingerprint`** *(property)*: sha256 over ids, inputs and references only: two runs of different systems on the same test set match.
- **`Dataset.filter(predicate: Callable[[Sample], bool], *, name: str | None = None) -> Dataset`**
- **`Dataset.with_tag(tag: str) -> Dataset`**
- **`Dataset.sample(n: int, *, seed: int = 0) -> Dataset`**
- **`Dataset.split(fraction: float, *, seed: int = 0) -> tuple[Dataset, Dataset]`**
- **`Dataset.map(fn: Callable[[Sample], Sample]) -> Dataset`**
- **`Dataset.to_records() -> list[dict[str, Any]]`**
- **`Dataset.save(path: str | Path) -> Path`**
- **`Dataset.stats() -> dict[str, Any]`**  
  Which fields are populated, tag counts and text lengths: what can be measured on this data.

### `load_dataset`

```python
load_dataset(path: str | Path, *, name: str | None = None) -> Dataset
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/dataset.py#L346)

Load a dataset file (`.jsonl`, `.json`, `.yaml`, `.csv`, `.tsv`).

### `normalise_record`

```python
normalise_record(record: dict[str, Any], index: int) -> dict[str, Any]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/dataset.py#L54)

Map a raw record onto sample fields. Unknown keys move into `metadata`.

## `guage_kit.core.results`

What an evaluation produces: per-sample scores, per-metric summaries, slices, a gate verdict and provenance.

### `Environment`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/results.py#L112)

Where a run happened: Guage Kit, Ananke Plexus and Python versions, platform and git state (recorded in
every run so results can be reproduced and compared fairly).

| field | type | default |
| --- | --- | --- |
| `guage_kit` | `str` | required |
| `ananke_plexus` | `str \| None` | `None` |
| `python` | `str` | `''` |
| `platform` | `str` | `''` |
| `git` | `dict[str, Any]` | `{}` |


### `GateCheck`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/results.py#L87)

The result of one gate rule: the metric's value, the rule it was checked against, whether it passed and a
human-readable message.

| field | type | default |
| --- | --- | --- |
| `metric` | `str` | required |
| `value` | `float \| None` | required |
| `rule` | `GateRule` | required |
| `ok` | `bool` | required |
| `message` | `str` | required |


### `GateResult`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/results.py#L98)

A run's verdict (`PASS`, `WARN`, `REVIEW` or `BLOCK`), decided by Ananke Plexus's gate policy,
with every check and the evidence files written for it.

| field | type | default |
| --- | --- | --- |
| `verdict` | `Literal['PASS', 'WARN', 'REVIEW', 'BLOCK']` | required |
| `checks` | `list[GateCheck]` | `[]` |
| `evidence` | `list[str]` | `[]` |
| `decided_by` | `str` | `'ananke.plexus.evals.policy.apply_gate_policy'` |


### `GateRule`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/results.py#L77)

A quality bar for one metric.

| field | type | default |
| --- | --- | --- |
| `metric` | `str` | required |
| `min` | `float \| None` | `None` |
| `max` | `float \| None` | `None` |
| `on_fail` | `Literal['block', 'warn', 'review']` | `'block'` |
| `max_drop` | `float \| None` | `None` |


### `MetricSummary`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/results.py#L47)

Aggregate of one metric over a run (or a slice of it).

| field | type | default |
| --- | --- | --- |
| `metric` | `str` | required |
| `family` | `str` | `''` |
| `description` | `str` | `''` |
| `higher_is_better` | `bool` | `True` |
| `level` | `Literal['sample', 'corpus']` | `'sample'` |
| `n` | `int` | `0` |
| `skipped` | `int` | `0` |
| `errors` | `int` | `0` |
| `value` | `float \| None` | `None` |
| `mean` | `float \| None` | `None` |
| `median` | `float \| None` | `None` |
| `std` | `float \| None` | `None` |
| `min` | `float \| None` | `None` |
| `max` | `float \| None` | `None` |
| `ci_low` | `float \| None` | `None` |
| `ci_high` | `float \| None` | `None` |
| `threshold` | `float \| None` | `None` |
| `pass_rate` | `float \| None` | `None` |
| `histogram` | `list[int]` | `[]` |
| `histogram_range` | `tuple[float, float] \| None` | `None` |
| `details` | `dict[str, Any]` | `{}` |


### `RunResult`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/results.py#L123)

A complete, self-describing evaluation run. Saved as `run.json` and rendered into reports.

| field | type | default |
| --- | --- | --- |
| `schema` | `str` | `'guage-kit/run@1'` |
| `run_id` | `str` | required |
| `name` | `str` | `''` |
| `created_at` | `str` | `''` |
| `duration_s` | `float` | `0.0` |
| `dataset` | `dict[str, Any]` | `{}` |
| `target` | `dict[str, Any]` | `{}` |
| `metrics` | `list[str]` | `[]` |
| `config` | `dict[str, Any]` | `{}` |
| `samples` | `list[SampleResult]` | `[]` |
| `summaries` | `dict[str, MetricSummary]` | `{}` |
| `slices` | `dict[str, dict[str, MetricSummary]]` | `{}` |
| `gate` | `GateResult \| None` | `None` |
| `judge` | `dict[str, Any]` | `{}` |
| `environment` | `Environment \| None` | `None` |
| `notes` | `list[str]` | `[]` |

- **`RunResult.value(metric: str) -> float | None`**
- **`RunResult.scores(metric: str) -> list[float]`**  
  Per-sample values of a metric (skipped and errored samples left out).
- **`RunResult.table() -> list[dict[str, Any]]`**  
  Summary rows for printing or a DataFrame.
- **`RunResult.to_json() -> str`**
- **`RunResult.save(path: str | Path) -> Path`**

### `SampleResult`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/results.py#L26)

One sample's outcome in a run: its input, output and expected value as evaluated, its tags, a
`Score` per metric, the target's error if it failed, and its latency.

| field | type | default |
| --- | --- | --- |
| `sample_id` | `str` | required |
| `input` | `Any` | `None` |
| `output` | `Any` | `None` |
| `expected` | `Any` | `None` |
| `tags` | `list[str]` | `[]` |
| `scores` | `dict[str, Score]` | `{}` |
| `target_error` | `str \| None` | `None` |
| `latency_ms` | `float \| None` | `None` |
| `repeats` | `list[Any]` | `[]` |


### `Score`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/core/results.py#L14)

One metric's result for one sample.

| field | type | default |
| --- | --- | --- |
| `metric` | `str` | required |
| `value` | `float \| None` | `None` |
| `passed` | `bool \| None` | `None` |
| `skipped` | `bool` | `False` |
| `error` | `str \| None` | `None` |
| `reason` | `str \| None` | `None` |
| `details` | `dict[str, Any]` | `{}` |


### `Verdict`

```python
Verdict(*args, **kwargs)
```
