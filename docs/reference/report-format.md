---
title: Run and report formats
description: The run.json schema, the comparison schema and the manifest embedded in HTML reports.
---

# Run and report formats

## `run.json` (`guage-kit/run@1`)

Written by `RunResult.save(path)`, by `--json-out` or `reports.json`, and under `.guage/runs/<run_id>/run.json`.
Read it back with `RunResult.load(path)`.

| Field | Type | |
| --- | --- | --- |
| `schema` | string | `guage-kit/run@1` |
| `run_id` | string | `YYYYMMDD-HHMMSS-<microseconds>-<4 hex>` (UTC) |
| `name` | string | run or suite name |
| `created_at` | ISO 8601 string | honours `SOURCE_DATE_EPOCH` for reproducible output |
| `duration_s` | number | |
| `dataset` | object | `name`, `source` (path), `fingerprint`, `input_fingerprint`, `samples` (count) |
| `target` | object | empty when Guage Kit did not run a target; otherwise `name`, `kind` (`callable` or `provider`) and its options |
| `metrics` | list of strings | display names, in order |
| `config` | object | `metrics` (each with `name`, `metric`, `params`, `threshold`), `confidence`, `n_resamples`, `seed`, `repeats`, `slices`, `embedder`, `gates`, and the whole `suite` when run from a suite |
| `samples` | list | one `SampleResult` per sample, below |
| `summaries` | object | metric name → `MetricSummary`, below |
| `slices` | object | `"<key>=<value>"` → metric name → `MetricSummary` |
| `gate` | object or null | `verdict` (`PASS`/`WARN`/`REVIEW`/`BLOCK`), `checks` (each `metric`, `value`, `rule`, `ok`, `message`), `evidence` (lines from Ananke's policy engine and Guage Kit's checks), `decided_by` |
| `judge` | object | empty without a judge; otherwise `judge`, `prompt_version`, `calls`, `cache_hits`, `input_tokens`, `output_tokens`, `errors` |
| `environment` | object | `guage_kit`, `ananke_plexus`, `python`, `platform`, `git` (`commit`, `dirty`, when in a git repository) |
| `notes` | list of strings | for example target failures, or a baseline that couldn't be compared |

### `SampleResult`

`sample_id`, `input`, `output`, `expected`, `tags`, `scores` (metric → `Score`), `target_error` (string or null),
`latency_ms`, `repeats` (extra outputs when `repeats > 1`).

A `Score` is `metric`, `value` (number or null), `passed` (with a threshold; otherwise null), `skipped`, `error`,
`reason`, `details` (metric-specific: claim tables, missing tools, schema errors, Ananke statuses…).

### `MetricSummary`

`metric`, `family`, `description`, `higher_is_better`, `level` (`sample`/`corpus`), `n`, `skipped`, `errors`,
`value` (the headline: the mean, or the corpus value), `mean`, `median`, `std`, `min`, `max`, `ci_low`, `ci_high`,
`threshold`, `pass_rate`, `histogram` (10 counts), `histogram_range` (`[low, high]`), `details` (corpus extras:
`confusion_matrix` and `labels`, `per_label`, `reliability`, BLEU `precisions` and `brevity_penalty`, `n`, …; `judge:
true` for non-deterministic metrics).

## Comparison (`guage-kit/comparison@1`)

`guage compare --json` and `Comparison.model_dump(by_alias=True)`:

| Field | |
| --- | --- |
| `schema` | `guage-kit/comparison@1` |
| `run_a`, `run_b` | `run_id`, `name`, `created_at`, `dataset`, `target` of the baseline and the candidate |
| `same_data` | whether the input fingerprints match |
| `common_samples` | number of shared sample ids |
| `metrics` | metric → `metric`, `level`, `higher_is_better`, `a`, `b`, `delta`, `ci_low`, `ci_high`, `p_value`, `p_adjusted`, `effect_size`, `wins`, `losses`, `ties`, `n`, `direction` |
| `regressions`, `improvements` | up to 10 each: `sample_id`, `metric`, `a`, `b`, `delta`, `input`, `output_a`, `output_b` |
| `pairwise` | the head-to-head judge result, or null |
| `alpha`, `min_effect` | the settings used |

## Report manifest (`guage-kit/report-manifest@1`)

Embedded in every HTML report as `<script type="application/json" id="guage-manifest">`:

```json
{"schema": "guage-kit/report-manifest@1", "renderer": "guage-kit/report-html@1", "guage_kit": "0.1.0",
 "ananke_plexus": "0.3.46", "view_model": "guage-kit/report-view@1", "profile": "public",
 "run_id": "20261124-060514-715322-cbb5", "dataset_fingerprint": "sha256:28bc…",
 "input_digest": "sha256:d38c…", "publication": "offline-single-file",
 "limitations": ["public profile: inputs, outputs, references, score explanations and the git revision were removed"]}
```

`input_digest` is a SHA-256 of the embedded view model (`<script id="guage-data">`), so you can check that a shared
report hasn't been edited. The view model (`guage-kit/report-view@1`) holds the run, summaries, slices, gate,
samples (without text under the public profile), comparison and limitations. It is an internal format of the report
page and may change between versions; use `run.json` for tooling.
