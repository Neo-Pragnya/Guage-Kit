---
title: Ananke integration
description: How Guage Kit negotiates the Ananke Plexus version, which Ananke interfaces it calls, how it converts samples and runs to Ananke's model, and where evidence goes.
---

# Ananke integration

## Version negotiation

Guage Kit supports Ananke Plexus `>=0.3.46,<0.4` (`SUPPORTED_ANANKE` in `guage_kit.harness.negotiation`, kept in step
with the dependency in `pyproject.toml` by a test). Negotiation is explicit: Guage Kit reads the installed version,
checks it against the range, and probes the interfaces it calls by importing them (nothing runs):

| Capability | Interface | Required |
| --- | --- | --- |
| `evals.models` | `ananke.plexus.evals.models.EvalScore` | yes |
| `evals.trace` | `ananke.plexus.evals.models.AgentTrace` | yes |
| `evals.normalize` | `ananke.plexus.evals.traces.normalize.normalize_trace` | yes |
| `evals.gate` | `ananke.plexus.evals.policy.decisions.apply_gate_policy` | yes |
| `evals.evaluators` | `ananke.plexus.evals.evaluators.base.Evaluator` | yes |
| `evals.evidence` | `ananke.plexus.evals.runner.save_eval_evidence` | |
| `evals.statistics` | `ananke.plexus.evals.regression.statistics.summary_statistics` | |
| `evals.judge_envelope` | `ananke.plexus.evals.judges.base.JudgeInputEnvelope` | |
| `evals.judge_agreement` | `ananke.plexus.evals.evaluators.meta.calibration.judge_human_agreement` | |
| `evals.markdown`, `evals.junit` | Ananke's report generators | |

```bash
guage doctor          # human-readable; exits 2 when the harness is incompatible
guage doctor --json   # {"harness": {"ananke_version", "supported_range", "compatible", "capabilities", "missing_required", "reasons"}, ...}
```

An out-of-range or incomplete harness is reported with the reasons (code `GK-HARNESS-001`), never silently worked
around.

## The evaluator catalogue

`guage_kit.harness.catalogue.discover()` walks `ananke.plexus.evals.evaluators` in the installed package and finds
every evaluator class (a class with an `id` and an `evaluate` method), with its dimension, determinism, constructor
arguments and their types. `register_all()` registers each one as a metric named by its Ananke id. Running one
(`run_evaluator(id, sample, config)`) resolves its constructor arguments (see [Agents](../guides/agents.md#configuring-an-evaluator)),
builds the case and trace, calls `evaluate`, and maps Ananke's scores to a Guage Kit score:

- the value is the mean of Ananke's normalised scores (or 1 for pass/warn and 0 for fail where there is none);
- it passes when every Ananke score passes;
- skipped-only results become a skip with Ananke's reason; error-only results become an error;
- Ananke's metric names, statuses, values and evidence go into the details.

## Conversions

| From (Guage Kit) | To (Ananke) | Function |
| --- | --- | --- |
| `Sample` | `EvalCase`: id, input, expected (or the first reference), metadata (plus `relevant_docs` from `relevant_ids`), tags | `harness.convert.to_case` |
| `Sample` with `trace` | `AgentTrace`, normalised by Ananke's `normalize_trace` | `to_trace` |
| `Sample` without `trace` | `AgentTrace` with a retrieval span (contexts), one tool span per tool call (errors as attributes and events), the final output, usage and latency | `to_trace` |
| `RunResult` summaries | one `EvalScore` per metric: dimension = family, metric = name, value, normalised score when in [0, 1], status from the gate rule | `to_scores` |
| gate rules | `GatePolicy` of `GatePolicyRule(minimum, maximum, on_failure)` keyed by metric | `to_policy` |
| `RunResult` | `EvalReport` with scores, the gate decision and a summary | `to_report` |

The gate itself is `harness.convert.gate(run, rules)`: Ananke's `apply_gate_policy` decides the verdict, and Guage Kit
adds per-rule checks and the [missing-value rule](../guides/gates-and-ci.md#missing-values).

## Evidence

`write_evidence(run, project_root, rules)` (or `--evidence`) calls Ananke's `save_eval_evidence`:

```text
<project>/.ananke/evidence/<run_id>/eval/
├── scores.json
├── policy-decision.json
├── manifest.json
└── reports/{report.md, summary.json, junit.xml}
```

Ananke reads it like any other evaluation evidence, for example `ananke eval report --run <run_id>`. In an
Ananke-governed repository, attach this evidence to the change it measured.
