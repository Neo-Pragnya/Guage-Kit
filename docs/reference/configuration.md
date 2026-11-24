---
title: Configuration (guage.yaml)
description: Every key of a Guage Kit suite file, with types and defaults, and an annotated complete example.
---

# Configuration: `guage.yaml`

A suite describes one evaluation, is versioned with your code, and is run with `guage run [path]` (default
`./guage.yaml`). Unknown keys are rejected with `GK-CONFIG-001`, so a typo fails instead of being ignored.

Relative paths (the dataset and report files) are relative to the suite file's folder. Runs are saved under
`<suite folder>/.guage/runs/`, baselines under `.guage/baselines/`, and the judge cache under `.guage/cache/judge/`.

## Keys

| Key | Type | Default | |
| --- | --- | --- | --- |
| `name` | string | `evaluation` | run name, shown in reports |
| `description` | string | `""` | |
| `dataset` | path | **required** | `.jsonl`, `.json`, `.yaml`, `.csv` or `.tsv` ([Datasets](../guides/datasets.md)) |
| `target` | string | none | `module:function` or a provider spec ([Targets](../guides/targets.md)) |
| `target_options` | map | `{}` | for a function: `retries`, `backoff_s`; for a provider: `system`, `template`, `retries` |
| `judge` | string | none | `heuristic` or a provider spec ([Judges](../guides/judges.md)) |
| `judge_options` | map | `{}` | for a model judge: `samples` (self-consistency) and `provider_options` (for Claude: `fallbacks`, `effort`, `max_tokens`) |
| `embedder` | string | none (hashing when a metric needs one) | `hashing` or a sentence-transformers model name |
| `metrics` | list or `auto` | `auto` | names or `{name, params, threshold, as}` specs ([Metrics](../guides/metrics.md)) |
| `slices` | list of strings | `[]` | `tags` and/or metadata keys |
| `gates` | list of rules | `[]` | `{metric, min, max, on_fail, max_drop}` ([Gates](../guides/gates-and-ci.md)) |
| `baseline` | run reference | none | compare with it and apply `max_drop` rules (`baseline:main`, a run id or path) |
| `repeats` | int | 1 | target calls per sample |
| `concurrency` | int | 4 | parallel target calls and judged metrics |
| `confidence` | float | 0.95 | interval level |
| `seed` | int | 0 | bootstrap and sampling seed |
| `limit` | int | none | evaluate only the first N samples |
| `reports` | map | none written | see below |
| `evidence` | bool | false | also write an Ananke evidence bundle |

### `reports`

| Key | Type | |
| --- | --- | --- |
| `html` | path | the HTML report |
| `json` | path | the full run (`run.json` format) |
| `junit` | path | JUnit XML |
| `markdown` | path | Markdown summary |
| `profile` | `private` \| `public` | default `private`; `public` removes sample text from the HTML |

Command-line flags override suite values: `--metrics`, `--target`, `--judge`, `--gate` (replaces `gates`), `--slice`,
`--repeats`, `--limit`, `--evidence`, `--baseline`, `--html`, `--json-out`, `--junit`, `--markdown` and `--profile`.

## A complete example

```yaml
name: support-assistant
description: Answers questions about Lumen Notes from the help centre.

dataset: data/support.jsonl              # relative to this file

target: support_bot.pipeline:answer      # called for samples without an output
target_options:
  retries: 2

judge: anthropic:claude-opus-5-5         # or heuristic (offline)
judge_options:
  samples: 1
  provider_options:
    fallbacks: true                      # server-side refusal fallbacks (the default)

embedder: hashing

metrics:
  - token_f1
  - recall@5
  - mrr
  - ndcg@10
  - {name: faithfulness, threshold: 0.8}
  - {name: faithfulness, params: {method: judge}, as: faithfulness_judged}
  - context_recall
  - {name: judge, params: {criterion: correctness}, as: judge_correctness}
  - latency_p95
  - pii_leakage

slices: [tags, difficulty]

gates:
  - {metric: faithfulness, min: 0.85}                       # block
  - {metric: recall@5, min: 0.8, on_fail: warn}
  - {metric: judge_correctness, min: 0.7, on_fail: review}
  - {metric: latency_p95, max: 1500, on_fail: warn}
  - {metric: pii_leakage, max: 0.0}
  - {metric: token_f1, max_drop: 0.02}                      # versus the baseline

baseline: baseline:main
repeats: 1
concurrency: 8
confidence: 0.95
seed: 0

reports:
  html: reports/guage-report.html
  json: reports/run.json
  junit: reports/guage-junit.xml
  markdown: reports/guage-summary.md
  profile: private

evidence: true
```

This example loads with `load_suite` (checked while writing these docs). Running it needs your `support_bot` package
and an Anthropic key.
