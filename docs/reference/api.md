---
title: "API reference"
description: "The complete Python API and CLI of Guage Kit, generated from the code."
---

# API reference

Everything a program can import from Guage Kit, and every option of the `guage` command, generated from the
installed package. For a guided tour start with the [Python API guide](python-api.md); for the metrics
themselves see the [metric reference](metrics.md).

| page | covers |
| --- | --- |
| [Evaluation and comparison](api/evaluation.md) | evaluate(), compare(), run storage and targets: the functions that produce and compare runs. |
| [Samples, datasets and results](api/data.md) | The data model: Sample, Dataset, and the run records (RunResult, Score, MetricSummary, gates). |
| [Metric registry and plugins](api/metrics.md) | Declaring metrics, resolving metric specs, the registry, metric cards and embedders. |
| [Judges and providers](api/judges.md) | LLM and heuristic judges, criteria, calibration against human labels, and model providers. |
| [Statistics](api/statistics.md) | Bootstrap intervals, paired tests, multiple-comparison correction, effect sizes and sample-size planning. |
| [Probes and synthetic data](api/probes-and-synthesis.md) | Perturbations, robustness runs, red-team datasets and test sets generated from your documents. |
| [Reports](api/reports.md) | The offline HTML report, Markdown summaries, JUnit XML and the report view model. |
| [Suites and configuration](api/configuration.md) | guage.yaml suites as Python objects: loading, running and writing configured reports. |
| [Ananke Plexus harness](api/ananke-harness.md) | Version negotiation, evaluator discovery and conversion between Guage Kit and Ananke Plexus models. |
| [Errors](api/errors.md) | GuageError and the GK-* error codes. |
| [Judge criteria](api/criteria.md) | Every built-in criterion with its score anchors. |
| [Perturbations](api/perturbations.md) | Every robustness perturbation. |
| [Statistical methods](api/statistical-methods.md) | Assumptions and papers behind every statistical method. |
| [CLI options](api/cli-options.md) | Every `guage` command, argument and option. |
