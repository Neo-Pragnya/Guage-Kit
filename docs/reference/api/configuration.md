---
title: "Suites and configuration"
description: "guage.yaml suites as Python objects: loading, running and writing configured reports."
---

# Suites and configuration

> [!NOTE]
> Generated from the code by `scripts/gen_api_docs.py`; signatures and docstrings are the installed
> package's.

The YAML keys are documented in the [configuration reference](../configuration.md).

## `guage_kit.config`

Suites: an evaluation described in `guage.yaml`, versioned with your code and run with `guage run`.

.. code-block:: yaml

    name: support-bot
    dataset: data/support.jsonl
    target: support_bot.pipeline:answer      # optional: module:function or a provider spec
    judge: anthropic:claude-opus-5-5         # or heuristic (offline), ollama:llama3.1, …
    metrics:
      - token_f1
      - recall@5
      - {name: faithfulness, threshold: 0.8}
      - {name: judge, params: {criterion: correctness}, as: judge_correctness}
    slices: [tags, difficulty]
    gates:
      - {metric: faithfulness, min: 0.85}
      - {metric: judge_correctness, min: 0.7, on_fail: warn}
      - {metric: token_f1, max_drop: 0.02}  # versus the baseline
    baseline: baseline:main
    reports: {html: reports/eval.html, junit: reports/eval.xml, markdown: reports/eval.md}

### `STARTER`

```python
STARTER = '# Guage Kit suite. Run it with: guage run\nname: {name}\ndataset: data/sample.jsonl\n# target: my_package.pipeline:answer     # the system under test (module:function or a provider spec)\njudge: heuristic                         # offline; for a model judge: anthropic:claude-opus-5-5\nmetrics: auto …
```

### `Reports`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/config.py#L35)

Which report files a suite writes (`html`, `json`, `junit`, `markdown`), relative to the suite file,
and the privacy profile: `private` keeps sample text, `public` removes it.

| field | type | default |
| --- | --- | --- |
| `html` | `str \| None` | `None` |
| `json` | `str \| None` | `None` |
| `junit` | `str \| None` | `None` |
| `markdown` | `str \| None` | `None` |
| `profile` | `Literal` | `'private'` |


### `Suite`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/config.py#L47)

A `guage.yaml` suite: the dataset, the optional target, judge and embedder, the metrics (or `auto`),
slices, gate rules, baseline, repeats and reports. Unknown keys are rejected so typos fail loudly.

| field | type | default |
| --- | --- | --- |
| `name` | `str` | `'evaluation'` |
| `description` | `str` | `''` |
| `dataset` | `str` | required |
| `target` | `str \| None` | `None` |
| `target_options` | `dict` | `{}` |
| `judge` | `str \| None` | `None` |
| `judge_options` | `dict` | `{}` |
| `embedder` | `str \| None` | `None` |
| `metrics` | `Union` | `'auto'` |
| `slices` | `list` | `[]` |
| `gates` | `list` | `[]` |
| `baseline` | `str \| None` | `None` |
| `repeats` | `int` | `1` |
| `concurrency` | `int` | `4` |
| `confidence` | `float` | `0.95` |
| `seed` | `int` | `0` |
| `limit` | `int \| None` | `None` |
| `reports` | `Reports` | `Reports(html=None, json_=None, junit=None, markdown=None, profile='private')` |
| `evidence` | `bool` | `False` |

- **`Suite.model_post_init(context: Any) -> None`**  
  This function is meant to behave like a BaseModel method to initialize private attributes.

It takes context as an argument since that's what pydantic-core passes when calling it.

Args:
    self: The BaseModel instance.
    context: The context.

### `load_suite`

```python
load_suite(path: str | Path) -> Suite
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/config.py#L79)

Read and validate a `guage.yaml` suite. Relative paths inside it resolve against the suite's folder.

Raises `GuageError` `GK-CONFIG-001` when the file is missing or invalid.

### `run_suite`

```python
run_suite(
    suite: Suite,
    *,
    overrides: dict[str, Any] | None = None,
    progress: Any = None,
) -> tuple[RunResult, Any]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/config.py#L103)

Run a suite: evaluate, gate (Ananke), compare with the baseline, write the configured reports.

Returns `(run, comparison_or_None)`. A `max_drop` rule that the candidate exceeds versus the baseline turns
the verdict into its `on_fail` level.

### `write_configured_reports`

```python
write_configured_reports(
    run: RunResult,
    reports: Reports,
    base: Path,
    comparison: Any = None,
) -> dict[str, Path]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/config.py#L202)

Write the reports a suite asks for and return their paths by kind (`html`, `json`, `junit`,
`markdown`). Relative paths resolve against `base`.
