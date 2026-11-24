---
title: "CLI options"
description: "Every guage command with every argument and option (generated from the CLI)."
---

# CLI options

> [!NOTE]
> Generated from the CLI by `scripts/gen_api_docs.py`. The [CLI guide](../cli.md) explains the
> commands with examples. Exit codes: 0 success, 1 a gate or regression failed, 2 a usage or `GK-*` error.

## `guage baseline set`

Copy a run to .guage/baselines/<name>.json (use it as baseline:<name>).

| name | kind | default | description |
| --- | --- | --- | --- |
| `RUN_REF` | argument, optional | `'latest'` | – |
| `--name` | option | `'main'` | – |

## `guage baseline show`

Print a baseline's metrics.

| name | kind | default | description |
| --- | --- | --- | --- |
| `--name` | option | `'main'` | – |

## `guage compare`

Compare two runs with paired statistics (bootstrap CI, permutation test, Holm correction).

| name | kind | default | description |
| --- | --- | --- | --- |
| `BASELINE` | argument, required | – | Baseline run (id, path, latest~1, baseline:<name>). |
| `CANDIDATE` | argument, optional | `'latest'` | Candidate run. |
| `-o`, `--output` | option | – | Write a comparison HTML report. |
| `--judge` | option | – | Also judge outputs head to head with this judge. |
| `--criterion` | option | `'helpfulness'` | – |
| `--min-effect` | option | `0.0` | Ignore changes smaller than this. |
| `--fail-on-regression` | flag | – | Exit 1 if any metric regressed significantly. |
| `--json` | flag | – | – |

## `guage data convert`

Convert between .jsonl, .json, .yaml and .csv (field aliases are normalised).

| name | kind | default | description |
| --- | --- | --- | --- |
| `SOURCE` | argument, required | – | – |
| `DEST` | argument, required | – | – |

## `guage data sample`

Write a reproducible random sample of n records.

| name | kind | default | description |
| --- | --- | --- | --- |
| `SOURCE` | argument, required | – | – |
| `-n` | option | – | – |
| `-o` | option | – | – |
| `--seed` | option | `0` | – |

## `guage data split`

Split into <name>.a.jsonl and <name>.b.jsonl (for dev/test or train/holdout).

| name | kind | default | description |
| --- | --- | --- | --- |
| `SOURCE` | argument, required | – | – |
| `--fraction` | option | `0.5` | – |
| `--seed` | option | `0` | – |

## `guage data stats`

Field coverage, tags and lengths, and the metrics `auto` would choose.

| name | kind | default | description |
| --- | --- | --- | --- |
| `PATH` | argument, required | – | – |
| `--json` | flag | – | – |

## `guage data validate`

Load a dataset and report problems (exit 2 on the first invalid record).

| name | kind | default | description |
| --- | --- | --- | --- |
| `PATH` | argument, required | – | – |

## `guage demo`

Evaluate three demo systems offline and write their reports (no model, no network).

| name | kind | default | description |
| --- | --- | --- | --- |
| `-o`, `--output` | option | `PosixPath('guage-demo')` | – |
| `--profile` | option | `'private'` | – |

## `guage doctor`

Check the Ananke harness, optional extras and provider credentials (names only, never values).

| name | kind | default | description |
| --- | --- | --- | --- |
| `--json` | flag | – | – |

## `guage init`

Write a starter guage.yaml and data/sample.jsonl (never overwrites).

| name | kind | default | description |
| --- | --- | --- | --- |
| `DIRECTORY` | argument, optional | `PosixPath('.')` | Where to write guage.yaml and a sample dataset. |
| `--name` | option | `'my-evaluation'` | – |

## `guage judge calibrate`

Grade labelled samples with a judge and report agreement with the human grades.

| name | kind | default | description |
| --- | --- | --- | --- |
| `DATA` | argument, required | – | Samples with a human score in metadata (see --human-field). |
| `--judge` | option | `'heuristic'` | – |
| `--criterion` | option | `'correctness'` | – |
| `--human-field` | option | `'human_score'` | metadata key holding the 1–5 human grade. |
| `--json` | flag | – | – |

## `guage metrics list`

List every metric with its family and required fields.

| name | kind | default | description |
| --- | --- | --- | --- |
| `--family`, `-f` | option | – | Only this family (prefix match, e.g. ananke). |
| `--json` | flag | – | – |

## `guage metrics show`

Show one metric: its declaration, what it measures, how it is computed, pitfalls and references.

| name | kind | default | description |
| --- | --- | --- | --- |
| `NAME` | argument, required | – | – |
| `--json` | flag | – | Print the declaration and card as JSON. |

## `guage probe perturb`

Write perturbed variants of a dataset's inputs (and contexts) for robustness runs.

| name | kind | default | description |
| --- | --- | --- | --- |
| `SOURCE` | argument, required | – | – |
| `-o` | option | – | – |
| `--kinds` | option | `'typos,lowercase,filler,distractor'` | – |
| `--seed` | option | `0` | – |

## `guage probe redteam`

Write a red-team dataset (prompt injection, extraction, PII, over-refusal). Run it with --target.

| name | kind | default | description |
| --- | --- | --- | --- |
| `-o` | option | `PosixPath('redteam.jsonl')` | – |
| `--system-prompt` | option | – | A file with your system prompt, to test leakage. |

## `guage probe robustness`

Run a target on originals and perturbed inputs; report output agreement and metric drops.

| name | kind | default | description |
| --- | --- | --- | --- |
| `SOURCE` | argument, required | – | – |
| `--target` | option | – | – |
| `--kinds` | option | `'typos,lowercase,filler,distractor'` | – |
| `--metrics` | option | – | – |
| `--json` | flag | – | – |

## `guage report`

Render the HTML report of a saved run.

| name | kind | default | description |
| --- | --- | --- | --- |
| `RUN_REF` | argument, optional | `'latest'` | Run id, path, latest or baseline:<name>. |
| `-o`, `--output` | option | `PosixPath('guage-report.html')` | – |
| `--profile` | option | `'private'` | – |
| `--against` | option | – | Include a comparison with this run. |

## `guage run`

Run an evaluation from a suite file or from flags, gate it and write reports.

| name | kind | default | description |
| --- | --- | --- | --- |
| `SUITE` | argument, optional | – | A guage.yaml suite (default: ./guage.yaml when --data is not given). |
| `--data`, `-d` | option | – | Dataset file (instead of a suite). |
| `--metrics`, `-m` | option | – | Comma-separated metrics (default: auto). |
| `--target` | option | – | module:function or a provider spec to produce outputs. |
| `--judge` | option | – | heuristic, anthropic:<model>, ollama:<model>, openai:<model> … |
| `--gate`, `-g` | option, repeatable | – | metric:min=V or metric:max=V (add :warn or :review), or a quoted 'metric>=V'; repeatable. |
| `--slice` | option, repeatable | – | tags or a metadata key; repeatable. |
| `--html` | option | – | Write the HTML report here. |
| `--junit` | option | – | – |
| `--markdown`, `--md` | option | – | – |
| `--json-out` | option | – | Write run.json here. |
| `--profile` | option | `'private'` | private or public (public removes sample text). |
| `--baseline` | option | – | Compare with a run id, path or baseline:<name>. |
| `--repeats` | option | – | – |
| `--limit` | option | – | Evaluate only the first N samples. |
| `--save`, `--no-save` | flag | `True` | Keep the run under .guage/runs. |
| `--evidence` | flag | – | Also write an Ananke evidence bundle. |
| `--fail-on` | option | `'block'` | Exit 1 at this verdict or worse: warn, review, block or never. |
| `--json` | flag | – | – |

## `guage runs`

List saved runs (newest first).

| name | kind | default | description |
| --- | --- | --- | --- |
| `--json` | flag | – | – |

## `guage synth`

Generate a test set from your own documents.

| name | kind | default | description |
| --- | --- | --- | --- |
| `PATHS` | argument, required | – | Documents or folders (.md, .txt, .rst, .html). |
| `-o` | option | `PosixPath('synthetic.jsonl')` | – |
| `--provider` | option | – | A model for natural questions; omit for offline cloze questions. |
| `--per-chunk` | option | `1` | – |
| `--corpus` | option | – | Also write the chunks (the corpus to index). |

## `guage version`

Print the Guage Kit and Ananke Plexus versions.

| name | kind | default | description |
| --- | --- | --- | --- |
| `--json` | flag | – | – |
