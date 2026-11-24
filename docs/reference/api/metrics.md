---
title: "Metric registry and plugins"
description: "Declaring metrics, resolving metric specs, the registry, metric cards and embedders."
---

# Metric registry and plugins

> [!NOTE]
> Generated from the code by `scripts/gen_api_docs.py`; signatures and docstrings are the installed
> package's.

Use `@metric` and `@corpus_metric` to add your own metrics; register them for other projects through the `guage_kit.metrics` entry-point group. Each built-in metric is described in the [metric reference](../metrics.md).

## `guage_kit.metrics.registry`

The metric registry: every metric, built in or your own, is a plain function with a declaration.

Sample metrics score one sample at a time::

    @metric("starts_with_greeting", family="custom", requires=("output",))
    def starts_with_greeting(sample: Sample, *, words: tuple[str, ...] = ("hi", "hello")) -> float:
        return float(sample.output_text.lower().startswith(words))

Corpus metrics see every sample at once (BLEU, macro-F1, ECE…)::

    @corpus_metric("label_entropy", family="custom", requires=("label",))
    def label_entropy(samples: list[Sample]) -> float: ...

A function may return a float, `(float, details)`, a `guage_kit.core.results.Score`, or `None` to skip
the sample. A parameter named `ctx` receives the `MetricContext` (judge, embedder). Parameters with
defaults are configurable from code or `guage.yaml`. `name@k` sets the parameter `k` (`recall@5`).
Third-party packages can register metrics through the `guage_kit.metrics` entry-point group.

### `REGISTRY`

```python
REGISTRY = <guage_kit.metrics.registry.MetricRegistry object>
```

### `BoundMetric`

```python
class BoundMetric(
    info: MetricInfo,
    name: str,
    params: dict[str, Any] = <factory>,
    threshold: float | None = None,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/registry.py#L262)

BoundMetric(info: 'MetricInfo', name: 'str', params: 'dict[str, Any]' = <factory>, threshold: 'float | None' = None)

- **`BoundMetric.missing(sample: Sample) -> list[str]`**
- **`BoundMetric.passed(value: float | None) -> bool | None`**
- **`BoundMetric.score(sample: Sample, ctx: MetricContext | None = None) -> Score`**
- **`BoundMetric.compute(samples: list[Sample], ctx: MetricContext | None = None) -> CorpusOutput`**

### `CorpusOutput`

```python
class CorpusOutput(
    value: float | None,
    details: dict[str, Any] = <factory>,
    per_sample: dict[str, float] = <factory>,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/registry.py#L255)

CorpusOutput(value: 'float | None', details: 'dict[str, Any]' = <factory>, per_sample: 'dict[str, float]' = <factory>)


### `MetricContext`

```python
class MetricContext(
    judge: Any = None,
    embedder: Any = None,
    seed: int = 0,
    options: dict[str, Any] = <factory>,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/registry.py#L85)

What a metric may use beyond the sample: a judge, an embedder and run-wide options.


### `MetricInfo`

```python
class MetricInfo(
    name: str,
    family: str,
    description: str,
    fn: Callable[..., Any],
    level: Level = 'sample',
    requires: tuple[str, ...] = (),
    requires_any: tuple[str, ...] = (),
    higher_is_better: bool = True,
    value_range: tuple[float | None, float | None] = (0.0, 1.0),
    deterministic: bool = True,
    needs_judge: bool = False,
    needs_embedder: bool = False,
    extra: str | None = None,
    params: dict[str, Any] = <factory>,
    preset: dict[str, Any] = <factory>,
    reference: str = '',
    source: str = 'guage-kit',
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/registry.py#L37)

MetricInfo(name: 'str', family: 'str', description: 'str', fn: 'Callable[..., Any]', level: 'Level' = 'sample', requires: 'tuple[str, ...]' = (), requires_any: 'tuple[str, ...]' = (), higher_is_better: 'bool' = True, value_range: 'tuple[float | None, float | None]' = (0.0, 1.0), deterministic: 'bool' = True, needs_judge: 'bool' = False, needs_embedder: 'bool' = False, extra: 'str | None' = None, params: 'dict[str, Any]' = <factory>, preset: 'dict[str, Any]' = <factory>, reference: 'str' = '', source: 'str' = 'guage-kit')

- **`MetricInfo.describe() -> dict[str, Any]`**

### `MetricRegistry`

```python
class MetricRegistry() -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/registry.py#L95)

The set of known metrics: built-in families, Ananke Plexus evaluators and plugins registered through the
`guage_kit.metrics` entry-point group. `REGISTRY` is the global instance.

- **`MetricRegistry.add(info: MetricInfo, *, replace: bool = False) -> MetricInfo`**
- **`MetricRegistry.variant(name: str, base: str, description: str = '', **preset: Any) -> MetricInfo`**  
  Register a named preset of another metric (`rouge1` is `rouge` with `variant='rouge1'`).
- **`MetricRegistry.get(name: str) -> MetricInfo`**
- **`MetricRegistry.all() -> list[MetricInfo]`**
- **`MetricRegistry.families() -> dict[str, list[str]]`**
- **`MetricRegistry.load_plugins() -> None`**  
  Import modules advertised in the `guage_kit.metrics` entry-point group (once).

### `corpus_metric`

```python
corpus_metric(
    name: str,
    *,
    family: str,
    description: str = '',
    requires: Sequence[str] = (),
    requires_any: Sequence[str] = (),
    higher_is_better: bool = True,
    value_range: tuple[float | None, float | None] = (0.0, 1.0),
    deterministic: bool = True,
    needs_judge: bool = False,
    needs_embedder: bool = False,
    extra: str | None = None,
    reference: str = '',
    registry: MetricRegistry | None = None,
    replace: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/registry.py#L178)

Register a function as a corpus-level metric, computed over all usable samples at once.

The function receives the list of samples that have the required fields and returns a float, a
`(value, details)` tuple or a `CorpusOutput`. Use it for statistics that are not averages of per-sample
scores (corpus BLEU, F1, ECE, percentiles). Confidence intervals come from resampling the samples. Other
arguments are as for `metric`.

### `get_metric`

```python
get_metric(name: str) -> MetricInfo
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/registry.py#L406)

The declaration (`MetricInfo`) of a registered metric. Raises `GK-METRIC-001` for unknown names,
suggesting the closest match.

### `list_metrics`

```python
list_metrics(family: str | None = None) -> list[dict[str, Any]]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/registry.py#L400)

Every registered metric's declaration (what `guage metrics list` prints).

### `metric`

```python
metric(
    name: str,
    *,
    family: str,
    description: str = '',
    requires: Sequence[str] = (),
    requires_any: Sequence[str] = (),
    higher_is_better: bool = True,
    value_range: tuple[float | None, float | None] = (0.0, 1.0),
    deterministic: bool = True,
    needs_judge: bool = False,
    needs_embedder: bool = False,
    extra: str | None = None,
    reference: str = '',
    registry: MetricRegistry | None = None,
    replace: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/registry.py#L178)

Register a function as a sample-level metric.

The function receives one `Sample` (and `ctx` if it declares it) and returns a float, a
`(value, details)` tuple, a `Score`, or None to skip the sample. Keyword-only parameters with defaults
become the metric's configurable `params`. `requires` lists sample fields that must be present (the sample
is skipped otherwise); `requires_any` needs at least one of them. The first paragraph of the docstring is the
description, unless `description` is given.

**Example**

```python
@metric("starts_polite", family="text", requires=("output",))
def starts_polite(sample, *, words=("hello", "hi")):
    """1 when the output opens with a greeting."""
    return float(sample.output_text.lower().startswith(tuple(words)))
```

### `resolve`

```python
resolve(
    spec: str | dict[str, Any] | BoundMetric,
    registry: MetricRegistry = <guage_kit.metrics.registry.MetricRegistry object>,
) -> BoundMetric
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/registry.py#L356)

Turn `"recall@5"`, `"bleu"` or `{"name": "rouge", "params": {...}, "threshold": 0.4, "as": "x"}`
into a bound metric, validating parameters.

## `guage_kit.metrics.cards`

Metric cards: the long-form documentation of every native metric, shipped with the package.

One YAML file per family under `guage_kit/metrics/cards/`. Each card says what the metric measures, how it is
computed, how to read it, its pitfalls, a worked example (checked by the test suite against the real metric) and
the papers or specifications that define it. `guage metrics show <name>` prints the card, and
`scripts/gen_metric_docs.py` renders them into the metric reference.

Card fields (all text is Markdown):

`summary`     one sentence, plain language
`measures`    the question the metric answers
`method`      how it is computed, step by step
`formula`     the formula in plain-text math (rendered as a code block)
`inputs`      which sample fields it reads and how
`params`      {name: explanation} for every configurable parameter
`interpret`   how to read the number, what good looks like
`use_when`    [situations it suits]
`pitfalls`    [ways it misleads]
`example`     {samples: [...], params: {...}, value: float, tolerance: float, note: str}
`related`     [other metric names]
`references`  [{citation: str, url: str}]

### `CARD_FIELDS`

```python
CARD_FIELDS = ('summary', 'measures', 'method', 'formula', 'inputs', 'params', 'interpret', 'use_when', 'pitfalls', 'example', 'related', 'references')
```

### `EVALUATOR_FIELDS`

```python
EVALUATOR_FIELDS = ('summary', 'method', 'arguments', 'passes_when', 'use_when', 'pitfalls', 'example', 'references')
```

### `REQUIRED_FIELDS`

```python
REQUIRED_FIELDS = ('summary', 'measures', 'method', 'inputs', 'interpret', 'pitfalls', 'references')
```

### `get_card`

```python
get_card(name: str) -> dict[str, Any] | None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/cards.py#L99)

The card for one metric (native or Ananke evaluator), or None (plugin metrics have none).

### `load_cards`

```python
load_cards() -> dict[str, dict[str, Any]]
```

Every card, keyed by metric name.

### `load_evaluator_cards`

```python
load_evaluator_cards() -> dict[str, dict[str, Any]]
```

Cards for the Ananke Plexus evaluators (`ananke.*` metrics), keyed by evaluator id.

Written from Ananke Plexus's source (one YAML file per dimension group under `cards/ananke/`): what the evaluator reads from the trace, when it passes, and what its
arguments mean. `example` is a suite snippet (YAML text), not executed. An evaluator added by a newer Ananke
Plexus release has no card until one is written; the reference then shows its one-line description.

## `guage_kit.metrics.semantic`

### `Embedder`

```python
class Embedder(*args, **kwargs)
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/semantic.py#L27)

What semantic metrics need from an embedding model: a `name` and `embed(texts)` returning one vector per
text. `HashingEmbedder` (offline, built in) and `SentenceTransformerEmbedder` implement it; any object with
these two members works.

- **`Embedder.embed(texts: list[str]) -> list[list[float]]`**

### `HashingEmbedder`

```python
class HashingEmbedder(dim: int = 1024) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/semantic.py#L45)

Offline embedder: hashed character 3–5-grams and words, sublinear tf, L2-normalised.

- **`HashingEmbedder.embed(texts: list[str]) -> list[list[float]]`**

### `SentenceTransformerEmbedder`

```python
class SentenceTransformerEmbedder(
    model: str = 'sentence-transformers/all-MiniLM-L6-v2',
    device: str | None = None,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/semantic.py#L74)

Embeddings from a sentence-transformers model (Apache-2.0). Models download on first use.

- **`SentenceTransformerEmbedder.embed(texts: list[str]) -> list[list[float]]`**
- **`SentenceTransformerEmbedder.token_embed(texts: list[str]) -> list[list[list[float]]]`**

### `make_embedder`

```python
make_embedder(spec: str | None) -> Embedder | None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/metrics/semantic.py#L99)

`"hashing"` → `HashingEmbedder`; any other string → a sentence-transformers model name.
