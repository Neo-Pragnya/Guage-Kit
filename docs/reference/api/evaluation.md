---
title: "Evaluation and comparison"
description: "evaluate(), compare(), run storage and targets: the functions that produce and compare runs."
---

# Evaluation and comparison

> [!NOTE]
> Generated from the code by `scripts/gen_api_docs.py`; signatures and docstrings are the installed
> package's.

The top-level package re-exports the everyday names (`from guage_kit import evaluate, compare, Dataset`). This page documents them where they are defined.

## `guage_kit.runner.evaluate`

`evaluate()`: run a target (optional), score every sample, aggregate with confidence intervals, slice, gate.

The whole run is described by the returned `guage_kit.core.results.RunResult`: data fingerprint, target,
metric parameters, judge usage, versions and git revision, so any report can say exactly what it measured.

### `auto_metrics`

```python
auto_metrics(samples: Sequence[Sample]) -> list[str]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/evaluate.py#L41)

Pick sensible metrics from which fields the data has. Explicit lists always win; this is the default.

### `environment`

```python
environment(root: Path | None = None) -> Environment
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/evaluate.py#L169)

Describe the current environment (versions, platform, git commit and dirty state) for a run record.

### `evaluate`

```python
evaluate(
    data: Dataset | Iterable[Sample | dict[str, Any]] | str | Path,
    metrics: Sequence[MetricSpec] | str | None = None,
    *,
    target: Any = None,
    judge: Any = None,
    embedder: Any = None,
    gates: Sequence[GateRule | dict[str, Any]] | None = None,
    slices: Sequence[str] | None = None,
    name: str = '',
    concurrency: int = 4,
    repeats: int = 1,
    confidence: float = 0.95,
    n_resamples: int = 1000,
    seed: int = 0,
    save: bool | str | Path = False,
    evidence: bool = False,
    project_root: str | Path = '.',
    progress: Callable[[str, int, int], None] | None = None,
    config: dict[str, Any] | None = None,
) -> RunResult
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/evaluate.py#L286)

Evaluate a dataset.

Args:
    data: a `Dataset`, a list of samples or dicts, or a dataset file path.
    metrics: metric names or specs (`"recall@5"`, `{"name": "judge", "params": {...}, "threshold": 0.7}`),
        or `None`/`"auto"` to choose from the fields the data has.
    target: the system under test (a callable, `module:function` or a provider spec), run for samples
        without an output. `repeats > 1` runs it several times and reports `self_consistency`.
    judge: a judge (`"heuristic"`, `"anthropic:claude-opus-5-5"`, `"ollama:llama3.1"` … or an object).
    embedder: an embedder (`"hashing"`, a sentence-transformers model name, or an object).
    gates: quality bars, `{"metric": "faithfulness", "min": 0.8, "on_fail": "block"}`. Decided by Ananke.
    slices: break results down by `"tags"` or by metadata keys (`"difficulty"`, `"language"`).
    save: write the run under `.guage/runs/` (`True`) or into the given directory.
    evidence: also write an Ananke evidence bundle under `.ananke/evidence/<run_id>/eval/`.

### `summarize`

```python
summarize(
    bm: BoundMetric,
    scores: list[Score],
    *,
    corpus_value: float | None = None,
    corpus_details: dict[str, Any] | None = None,
    confidence: float = 0.95,
    n_resamples: int = 1000,
    seed: int = 0,
) -> MetricSummary
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/evaluate.py#L190)

Summarise a metric over a run: mean of the sample scores (or the corpus value) with a bootstrap
confidence interval, counts of scored, skipped and errored samples, and a histogram.

## `guage_kit.runner.compare`

Compare two runs on the same data: which metrics really moved, which samples got worse, and is it significant?

For every sample-level metric both runs share, the comparison pairs samples by id and reports the mean difference
with a paired-bootstrap interval, a permutation-test p-value (Holm-adjusted across metrics), a sign test and an
effect size. Corpus metrics get their difference only (no per-sample test exists for them). A change is called
an improvement or a regression only when it is significant *and* larger than `min_effect`.

`pairwise` asks a judge which output is better, sample by sample, in both orders.

### `Comparison`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/compare.py#L62)

The result of comparing two runs: per-metric deltas, the largest per-sample regressions and
improvements, whether both runs used the same data, and an optional pairwise judge verdict.

| field | type | default |
| --- | --- | --- |
| `schema` | `str` | `'guage-kit/comparison@1'` |
| `run_a` | `dict` | required |
| `run_b` | `dict` | required |
| `same_data` | `bool` | required |
| `common_samples` | `int` | required |
| `metrics` | `dict` | `{}` |
| `regressions` | `list` | `[]` |
| `improvements` | `list` | `[]` |
| `pairwise` | `dict[str, Any] \| None` | `None` |
| `alpha` | `float` | `0.05` |
| `min_effect` | `float` | `0.0` |


### `MetricDelta`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/compare.py#L25)

How one metric changed between two runs: both values, the difference with its bootstrap interval, the
Holm-adjusted p-value, effect size, win/loss counts and a direction (improved, regressed, unchanged,
inconclusive, or changed for corpus metrics).

| field | type | default |
| --- | --- | --- |
| `metric` | `str` | required |
| `level` | `str` | `'sample'` |
| `higher_is_better` | `bool` | `True` |
| `a` | `float \| None` | `None` |
| `b` | `float \| None` | `None` |
| `delta` | `float \| None` | `None` |
| `ci_low` | `float \| None` | `None` |
| `ci_high` | `float \| None` | `None` |
| `p_value` | `float \| None` | `None` |
| `p_adjusted` | `float \| None` | `None` |
| `effect_size` | `float \| None` | `None` |
| `wins` | `int` | `0` |
| `losses` | `int` | `0` |
| `ties` | `int` | `0` |
| `n` | `int` | `0` |
| `direction` | `Literal` | `'inconclusive'` |


### `SampleDelta`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/compare.py#L48)

One sample's change on one metric between two runs, with both outputs (used for the largest
regressions and improvements).

| field | type | default |
| --- | --- | --- |
| `sample_id` | `str` | required |
| `metric` | `str` | required |
| `a` | `float` | required |
| `b` | `float` | required |
| `delta` | `float` | required |
| `input` | `Any` | `None` |
| `output_a` | `Any` | `None` |
| `output_b` | `Any` | `None` |


### `compare`

```python
compare(
    a: RunResult,
    b: RunResult,
    *,
    metrics: list[str] | None = None,
    alpha: float = 0.05,
    min_effect: float = 0.0,
    n_resamples: int = 2000,
    seed: int = 0,
    top: int = 10,
) -> Comparison
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/compare.py#L99)

Compare run `b` (candidate) against run `a` (baseline).

### `pairwise`

```python
pairwise(
    a: RunResult,
    b: RunResult,
    judge: Any,
    *,
    criterion: str = 'helpfulness',
    limit: int | None = None,
    seed: int = 0,
) -> dict[str, Any]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/compare.py#L207)

Judge each shared sample's two outputs head to head (both orders). Returns b's win rate with a CI.

### `regression_gate`

```python
regression_gate(comparison: Comparison, rules: list[Any]) -> list[str]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/compare.py#L272)

Messages for every rule whose `max_drop` the candidate exceeds versus the baseline.

## `guage_kit.runner.store`

Run storage: `.guage/runs/<run_id>/run.json`, `latest`, and named baselines in `.guage/baselines/`.

### `RunStore`

```python
class RunStore(root: str | Path = '.guage/runs') -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/store.py#L14)

Saved runs under `.guage/runs` and named baselines under `.guage/baselines`. `load` accepts a run id,
a path, `latest`, `latest~N` or `baseline:<name>`.

- **`RunStore.save(run: RunResult) -> Path`**
- **`RunStore.list() -> list[dict[str, Any]]`**
- **`RunStore.resolve(ref: str | Path) -> Path`**  
  A run id, `latest`, `latest~1`, `baseline:<name>`, a run directory or a run.json path.
- **`RunStore.load(ref: str | Path) -> RunResult`**
- **`RunStore.set_baseline(ref: str | Path, name: str = 'main') -> Path`**

### `load_run`

```python
load_run(ref: str | Path | RunResult, root: str | Path = '.guage/runs') -> RunResult
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/store.py#L91)

Load a run from a reference (run id, path, `latest`, `latest~N` or `baseline:<name>`); a
`RunResult` is returned unchanged.

## `guage_kit.runner.target`

Targets: the system under test. Guage Kit calls it for every sample that has no output yet.

A target is any callable. It receives the sample's `input` (or the whole `Sample` when its first
parameter is named `sample` or annotated `Sample`) and returns either the output text, or a dict that can also
carry `contexts`, `retrieved_ids`, `tool_calls`, `label`, `probabilities`, `confidence`, `usage`,
`trace` and `metadata`. That is how a RAG pipeline reports what it retrieved and an agent reports what it did.

Targets can also be named: `module:function` imports your function; a provider spec (`anthropic:claude-opus-5-5`,
`ollama:llama3.1` …) calls a model with an optional system prompt and prompt template.

### `ProviderTarget`

```python
class ProviderTarget(
    provider: str | Provider,
    *,
    system: str = 'You are a helpful assistant.',
    template: str = '{input}',
    retries: int = 2,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/target.py#L66)

Call a model directly: `template` formats the prompt from the sample (`{input}`, `{contexts}`, metadata keys).

- **`ProviderTarget.describe() -> dict[str, Any]`**

### `Target`

```python
class Target(
    fn: Callable[..., Any],
    *,
    name: str | None = None,
    retries: int = 0,
    backoff_s: float = 1.0,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/target.py#L26)

The system under test: a callable that receives a sample's input (or the whole sample, when its first
parameter is named `sample`) and returns an output. Retries with backoff on exceptions.

- **`Target.describe() -> dict[str, Any]`**

### `make_target`

```python
make_target(spec: Any, **options: Any) -> Target | None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/target.py#L173)

A callable, `module:function`, a provider spec, or an existing `Target`.

### `merge_output`

```python
merge_output(sample: Sample, raw: Any, elapsed_ms: float | None = None) -> Sample
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/runner/target.py#L127)

Merge what a target returned into the sample: a string becomes `output`; a mapping may also set
contexts, retrieved ids, tool calls, usage and other sample fields; a `Sample` replaces it.
