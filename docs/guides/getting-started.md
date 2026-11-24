---
title: Getting started
description: Install Guage Kit, write a suite with guage init, run it, open the report, and do the same from Python.
---

# Getting started

## Install

Guage Kit needs Python 3.11 or newer.

```bash
pip install guage-kit
# or
uv add guage-kit
```

The core install has no model dependencies. Optional extras add capabilities:

| Extra | Adds | Install |
| --- | --- | --- |
| `anthropic` | Claude as a judge or target, through the official Anthropic SDK | `pip install "guage-kit[anthropic]"` |
| `embeddings` | sentence-transformers models for semantic similarity and BERTScore-style matching | `pip install "guage-kit[embeddings]"` |
| `jsonschema` | full JSON Schema validation (a built-in validator covers the common keywords) | `pip install "guage-kit[jsonschema]"` |
| `bedrock` | Amazon Bedrock judges and targets (boto3) | `pip install "guage-kit[bedrock]"` |
| `all` | all of the above | `pip install "guage-kit[all]"` |

OpenAI-compatible servers (including Ollama, vLLM and LM Studio) need no extra.

Check the installation:

```bash
guage doctor
```

```text
Ananke Plexus 0.3.45 (>=0.3.45,<0.4): compatible
Metrics: 167 (77 from Ananke)
Extras: anthropic –, embeddings –, jsonschema –, bedrock –
Credentials: ANTHROPIC_API_KEY unset, OPENAI_API_KEY unset, GUAGE_OPENAI_COMPATIBLE_KEY unset,
OLLAMA_HOST unset
```

`doctor` reports whether credentials are set, never their values.

## Your first suite

```bash
mkdir my-eval && cd my-eval
guage init
```

```text
wrote guage.yaml
wrote data/sample.jsonl
Next: guage run  (then open reports/guage-report.html)
```

`guage init` never overwrites. It writes a suite and twelve sample records (a support assistant answering questions
about a notes app, with retrieved contexts and simulated outputs):

```yaml
# Guage Kit suite. Run it with: guage run
name: my-evaluation
dataset: data/sample.jsonl
# target: my_package.pipeline:answer     # the system under test (module:function or a provider spec)
judge: heuristic                         # offline; for a model judge: anthropic:claude-opus-5-5
metrics: auto                            # or a list, e.g. [token_f1, faithfulness, recall@5]
slices: [tags]
gates:
  - {metric: faithfulness, min: 0.7}
  - {metric: recall@5, min: 0.8, on_fail: warn}
reports:
  html: reports/guage-report.html
  junit: reports/guage-junit.xml
  markdown: reports/guage-summary.md
```

Run it:

```bash
guage run
```

The command prints a table of every metric with its 95% confidence interval, then the gate:

```text
Gate: PASS
  ✓ faithfulness: 0.75 meets ≥ 0.7
  ✓ recall@5: 1 meets ≥ 0.8
html: reports/guage-report.html
junit: reports/guage-junit.xml
markdown: reports/guage-summary.md
```

Open `reports/guage-report.html` in a browser. It is one offline file: overview tiles with intervals, a metrics table
with distributions, a slice heatmap, every sample with its scores and explanations, and the run's provenance. See
[Reports](reports.md).

`metrics: auto` picks metrics from the fields your data has. To choose them yourself, list them (see
[Metrics](metrics.md)). The run is saved under `.guage/runs/` so you can compare it with later runs:

```bash
guage baseline set            # the latest run becomes baseline:main
# ...change your system, then:
guage run --baseline baseline:main
```

## From Python

The same evaluation in code:

```python
import guage_kit as gk

run = gk.evaluate(
    "data/sample.jsonl",
    None,                                    # None or "auto": choose metrics from the data
    judge="heuristic",
    slices=["tags"],
    gates=[{"metric": "faithfulness", "min": 0.7},
           {"metric": "recall@5", "min": 0.8, "on_fail": "warn"}],
)
print(run.gate.verdict, run.value("faithfulness"))
gk.report(run, "report.html")
```

`evaluate` returns a [`RunResult`](../reference/report-format.md): per-sample scores, per-metric summaries with
confidence intervals, slices, the gate decision and provenance. Pass `save=True` to keep it under `.guage/runs/`.

## Evaluate your own system

Point a suite (or `evaluate`) at a function that calls your system, and Guage Kit fills in the outputs:

```yaml
target: my_package.pipeline:answer
```

The function receives the sample's input and returns the answer, or a dict with the answer plus what it retrieved,
which tools it called and how many tokens it used. See [Targets](targets.md).

## The demo

```bash
guage demo -o guage-demo
```

This evaluates three simulated systems offline and writes their reports: a RAG support assistant in two versions
(compared with paired statistics), a tool-using agent, and an intent classifier. Open
`guage-demo/support-assistant-v1-vs-v2.html`. The same reports are on the project website.
