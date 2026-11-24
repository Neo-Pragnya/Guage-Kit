# Guage Kit

**Measure every layer of an AI system: LLM answers, RAG pipelines, retrieval, embeddings, classifiers and agents.
Deterministic metrics first, LLM judges when you want them, real statistics, quality gates for CI, and one offline
HTML report per run. Built on the [Ananke Plexus](https://github.com/Neo-Pragnya/Ananke-Plexus) evaluation harness.**

[![PyPI](https://img.shields.io/pypi/v/guage-kit?label=PyPI&color=blue)](https://pypi.org/project/guage-kit/)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)](https://pypi.org/project/guage-kit/)
[![CI](https://github.com/Neo-Pragnya/Guage-Kit/actions/workflows/ci.yml/badge.svg)](https://github.com/Neo-Pragnya/Guage-Kit/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-website-teal.svg)](https://neo-pragnya.github.io/Guage-Kit/)

<p align="center"><img src="https://neo-pragnya.github.io/Guage-Kit/terminal.svg" alt="guage run and guage compare in a terminal" width="860"></p>

```bash
pip install guage-kit
guage demo            # three systems evaluated offline, reports written to ./guage-demo
```

## What it does

| | |
| --- | --- |
| **90 metrics, no model needed** | exact/normalised match, token F1, BLEU, chrF/chrF++, ROUGE-1/2/L/Lsum, edit distance; RAG faithfulness, hallucination rate, context precision/recall/relevance/utilisation, citation accuracy, answer correctness; precision/recall/hit@k, MRR, MAP, nDCG (graded); accuracy, macro/micro/weighted F1, kappa, MCC; ECE, MCE, Brier, selective AUROC; STS correlation, alignment, uniformity, anisotropy; JSON/YAML validity, JSON Schema, field accuracy; PII, secrets, prompt-injection, system-prompt leakage, refusals, toxicity, counterfactual consistency; tool-call F1, argument accuracy, sequence match; latency percentiles, tokens, cost |
| **77 agent evaluators from Ananke** | trajectory, tool use, planning, safety boundaries, resilience, efficiency, multi-agent hand-offs: discovered from the installed harness and run as `ananke.*` metrics |
| **LLM judges** | 11 anchored criteria or your own rubric; Claude (official SDK), OpenAI-compatible servers, Ollama, Bedrock or any function; on-disk cache, self-consistency, pairwise with order swapping, injection-safe prompts, agreement with human labels |
| **Statistics** | bootstrap confidence intervals on every number (corpus metrics too); paired bootstrap, permutation and sign tests with Holm correction for comparisons; sample-size planning |
| **Gates and CI** | `min`/`max`/`max_drop` rules decided by Ananke's policy engine into PASS, WARN, REVIEW or BLOCK; exit codes, JUnit XML, Markdown summaries, Ananke evidence bundles |
| **Reports** | one self-contained HTML file: overview, metric distributions, slices heatmap, every sample with its explanations, before/after comparison; offline and locked down by its Content Security Policy |
| **Everything else** | run your own system as a target, `guage.yaml` suites, a pytest plugin, robustness and red-team probes, synthetic test sets from your documents |

## Sixty seconds

```python
import guage_kit as gk

def my_rag(question: str) -> dict:          # your system under test
    docs = retriever.search(question, k=5)
    return {"output": llm.answer(question, docs), "contexts": [d.text for d in docs], "retrieved_ids": [d.id for d in docs]}

run = gk.evaluate(
    "support_questions.jsonl",               # question, ground_truth, relevant_ids per line
    ["token_f1", "faithfulness", "context_recall", "recall@5", "mrr",
     {"name": "judge", "params": {"criterion": "correctness"}, "as": "judge_correctness"}],
    target=my_rag,
    judge="anthropic:claude-opus-5-5",       # or "heuristic" to stay offline
    gates=[{"metric": "faithfulness", "min": 0.85}, {"metric": "recall@5", "min": 0.8, "on_fail": "warn"}],
    slices=["tags"],
)
print(run.gate.verdict, run.value("faithfulness"), run.summaries["faithfulness"].ci_low)
gk.report(run, "report.html")
```

Or from the command line:

```bash
guage init                                   # guage.yaml + a sample dataset
guage run                                    # evaluate, gate, write reports (exit 1 when the gate blocks)
guage baseline set                           # remember this run
guage run && guage compare baseline:main latest -o compare.html
```

In pytest:

```python
def test_answers_are_grounded(guage):
    run = guage.evaluate("tests/data/qa.jsonl", ["faithfulness", "recall@5"], target=my_rag)
    guage.check(run, faithfulness=0.85, recall__at__5=0.8)
```

## Install

```bash
pip install guage-kit                        # core: offline metrics, reports, CLI, pytest plugin
pip install "guage-kit[anthropic]"           # Claude judges and targets (official SDK)
pip install "guage-kit[embeddings]"          # sentence-transformers for semantic metrics
pip install "guage-kit[all]"                 # anthropic, embeddings, jsonschema, bedrock
```

Python 3.11–3.14. Every runtime dependency is permissively licensed (Apache-2.0, MIT, BSD, ISC, PSF; certifi is
MPL-2.0); `make licenses` checks it. See [licensing](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/concepts/licensing.md).

## Documentation

The full documentation is on the [website](https://neo-pragnya.github.io/Guage-Kit/) and in [docs/](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/index.md):
[getting started](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/guides/getting-started.md) · [datasets](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/guides/datasets.md) ·
[targets](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/guides/targets.md) · [metrics](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/guides/metrics.md) · [RAG](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/guides/rag.md) ·
[agents](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/guides/agents.md) · [judges](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/guides/judges.md) · [statistics](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/guides/statistics.md) ·
[gates and CI](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/guides/gates-and-ci.md) · [reports](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/guides/reports.md) · [pytest](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/guides/pytest.md) ·
[safety and red teaming](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/guides/safety-and-red-teaming.md) · [CLI](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/reference/cli.md) ·
[metric catalogue](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/reference/metrics.md) · [configuration](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/reference/configuration.md).

## How it relates to Ananke Plexus

Ananke Plexus owns the canonical evaluation model (cases, agent traces, scores), its agent evaluators, the gate
policy engine and evidence bundles. Guage Kit builds the evaluation product on top: the metric library, judges,
statistics, the runner, reports, CLI and pytest plugin. Results convert both ways, so a Guage Kit run can be filed as
Ananke evidence and gated by the same policy as the rest of an Ananke-governed project. See
[architecture](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/docs/concepts/architecture.md).

## Development

```bash
make install      # uv sync with dev tools
make verify       # ruff, format check, mypy --strict, pytest, licence check, generated docs check
make acceptance   # 47 capability scenarios driving the real CLI; the release gate
make scan         # build and scan the wheel and sdist the way package firewalls do
```

See [CONTRIBUTING.md](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/CONTRIBUTING.md) and [AGENTS.md](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/AGENTS.md). Licensed under [Apache-2.0](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/LICENSE).
