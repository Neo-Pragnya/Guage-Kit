---
title: Guage Kit
description: Measure LLMs, RAG pipelines, retrieval, embeddings, classifiers and agents with deterministic metrics, LLM judges, real statistics, quality gates and offline HTML reports.
---

# Guage Kit

[![PyPI](https://img.shields.io/pypi/v/guage-kit?label=PyPI&color=blue)](https://pypi.org/project/guage-kit/)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://pypi.org/project/guage-kit/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/LICENSE)

Guage Kit evaluates AI systems. You give it samples (inputs, the system's outputs, and whatever ground truth you
have) and it tells you how good the outputs are, how sure you can be about that number, whether a change made things
better or worse, and whether the result is good enough to ship.

It is a Python package (`guage-kit`), a command line (`guage`), a pytest plugin and a report generator. Everything
runs locally. No account, server or network access is needed unless you choose a model as a judge or as the system
under test.

## What it measures

| Area | Examples |
| --- | --- |
| Text against references | exact and normalised match, token F1, BLEU, chrF, ROUGE, edit distance, numeric match |
| RAG | faithfulness (claim by claim), hallucination rate, context precision and recall, answer relevancy, citation accuracy |
| Retrieval | precision@k, recall@k, hit rate, MRR, MAP, nDCG (binary or graded), R-precision |
| Classification and calibration | accuracy, F1 (macro, micro, weighted, binary), kappa, MCC, ECE, Brier, selective AUROC |
| Embeddings | STS Spearman and Pearson, alignment, uniformity, anisotropy, BERTScore-style matching |
| Structured output | valid JSON or YAML, JSON Schema conformance, field-level accuracy, Python that parses |
| Agents | tool-call F1, argument accuracy, sequence match, error and redundancy rates, plus 77 trace evaluators from Ananke Plexus |
| Safety | refusals and over-refusal, personal data and secret leakage, prompt-injection resistance, system-prompt leakage, toxicity, counterfactual consistency |
| Runtime | latency percentiles, tokens, cost |
| Judged quality | an LLM judge grading correctness, helpfulness, groundedness and eight more criteria, or your own rubric |

`guage metrics list` prints all of them (167 in this release). See the [metric reference](reference/metrics.md).

## Built on Ananke Plexus

Guage Kit is a client of [Ananke Plexus](concepts/ananke-integration.md), the local-first harness for governed agentic
engineering. Ananke owns the canonical evaluation model (cases, agent traces, scores), the agent-trace evaluators, the
gate policy engine and evidence bundles. Guage Kit adds the metric library, judges, statistics, the evaluation runner,
reports and the CLI, and it hands every gate decision to Ananke. The boundary is described in
[Architecture](concepts/architecture.md).

## In 60 seconds

```bash
pip install guage-kit
```

```python
import guage_kit as gk

samples = [
    gk.Sample(id="q1", input="How often does the app sync?",
              output="Every 30 seconds when you are online.",
              expected="Every 30 seconds when online.",
              contexts=["The app syncs every 30 seconds when you are online."],
              retrieved_ids=["kb-sync", "kb-export"], relevant_ids=["kb-sync"]),
    gk.Sample(id="q2", input="Can I export to PDF?",
              output="Yes, and to Word documents too.",
              expected="Yes, as Markdown, PDF or HTML.",
              contexts=["You can export a notebook as Markdown, PDF or HTML."],
              retrieved_ids=["kb-export"], relevant_ids=["kb-export"]),
]
run = gk.evaluate(samples, ["token_f1", "faithfulness", "recall@5", "mrr"],
                  gates=[{"metric": "faithfulness", "min": 0.8}])
for name, s in run.summaries.items():
    print(f"{name:14} {s.value:.3f}")
print("gate:", run.gate.verdict)
gk.report(run, "report.html")
```

```text
token_f1       0.500
faithfulness   0.500
recall@5       1.000
mrr            1.000
gate: BLOCK
```

The second answer adds a claim ("Word documents") that its context does not support, so faithfulness is 0.5 and the
gate blocks. `report.html` shows that claim, marked unsupported, next to the answer.

## Where to go next

**Start here**

- [Getting started](guides/getting-started.md): install, `guage init`, `guage run`, the demo.
- [Datasets](guides/datasets.md): the sample fields, file formats and automatic metric selection.
- [Targets](guides/targets.md): let Guage Kit call your system to produce outputs.

**By task**

- [Metrics](guides/metrics.md), including writing your own.
- [RAG](guides/rag.md), [agents](guides/agents.md), [classification and calibration](guides/classification-and-calibration.md), [embeddings](guides/embeddings.md).
- [LLM judges](guides/judges.md) and how to calibrate them.
- [Safety and red teaming](guides/safety-and-red-teaming.md), [robustness](guides/robustness.md), [synthetic test sets](guides/synthetic-data.md).
- [Statistics](guides/statistics.md): confidence intervals and comparing two runs.
- [Gates and CI](guides/gates-and-ci.md), [reports](guides/reports.md), [pytest](guides/pytest.md).
- [Releasing Guage Kit](guides/release.md) (for maintainers).

**Concepts**

- [Architecture](concepts/architecture.md), [Ananke integration](concepts/ananke-integration.md), [report safety](concepts/report-safety.md), [licensing](concepts/licensing.md).

**Reference**

- [CLI](reference/cli.md), [Python API](reference/python-api.md), [configuration (`guage.yaml`)](reference/configuration.md), [metrics](reference/metrics.md), [report and run formats](reference/report-format.md), [error codes](reference/errors.md).
- [Roadmap](roadmap.md).
