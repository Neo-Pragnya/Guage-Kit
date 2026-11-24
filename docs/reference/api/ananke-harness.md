---
title: "Ananke Plexus harness"
description: "Version negotiation, evaluator discovery and conversion between Guage Kit and Ananke Plexus models."
---

# Ananke Plexus harness

> [!NOTE]
> Generated from the code by `scripts/gen_api_docs.py`; signatures and docstrings are the installed
> package's.

How the two packages divide the work is explained in [Ananke integration](../../concepts/ananke-integration.md).

## `guage_kit.harness.negotiation`

Which Ananke Plexus this Guage Kit supports, and what the installed one can do.

Negotiation is explicit: Guage Kit reads the installed harness version, checks it against `SUPPORTED_ANANKE` and
probes the interfaces it calls. An out-of-range or incomplete harness is reported with a stable code
(`GK-HARNESS-001`) by `guage doctor`, never silently worked around.

### `CAPABILITIES`

```python
CAPABILITIES = {'evals.models': ('ananke.plexus.evals.models', 'EvalScore'), 'evals.trace': ('ananke.plexus.evals.models', 'AgentTrace'), 'evals.normalize': ('ananke.plexus.evals.traces.normalize', 'normalize_trace'), 'evals.gate': ('ananke.plexus.evals.policy.decisions', 'apply_gate_policy'), 'evals.evidence': (' …
```

### `REQUIRED`

```python
REQUIRED = ('evals.models', 'evals.trace', 'evals.normalize', 'evals.gate', 'evals.evaluators')
```

### `SUPPORTED_ANANKE`

```python
SUPPORTED_ANANKE = '>=0.3.45,<0.4'
```

### `check`

```python
check() -> dict[str, Any]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/negotiation.py#L82)

The negotiation verdict `guage doctor` prints.

### `installed_version`

```python
installed_version(distribution: str = 'ananke-plexus') -> str | None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/negotiation.py#L58)

The installed version of a distribution (Ananke Plexus by default), or None when it is not installed.

### `parse_version`

```python
parse_version(text: str) -> tuple[int, int, int] | None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/negotiation.py#L37)

Parse the leading `major.minor.patch` of a version string; None when it has none.

### `probe`

```python
probe(
    capabilities: dict[str, tuple[str, str]] = {'evals.models': ('ananke.plexus.evals.models', 'EvalScore'), 'evals.trace': ('ananke.plexus.evals.models', 'AgentTrace'), 'evals.normalize': ('ananke.plexus.evals.traces.normalize', 'normalize_trace'), 'evals.gate': ('ananke.plexus.evals.policy.decisions', 'apply_gate_policy'), 'evals.evidence': ('ananke.plexus.evals.runner', 'save_eval_evidence'), 'evals.evaluators': ('ananke.plexus.evals.evaluators.base', 'Evaluator'), 'evals.statistics': ('ananke.plexus.evals.regression.statistics', 'summary_statistics'), 'evals.judge_envelope': ('ananke.plexus.evals.judges.base', 'JudgeInputEnvelope'), 'evals.judge_agreement': ('ananke.plexus.evals.evaluators.meta.calibration', 'judge_human_agreement'), 'evals.markdown': ('ananke.plexus.evals.reports.markdown', 'generate_markdown_report'), 'evals.junit': ('ananke.plexus.evals.reports.junit', 'generate_junit_xml')},
) -> dict[str, bool]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/negotiation.py#L66)

Which capabilities the importable harness exposes (imports only; nothing runs).

### `supported`

```python
supported(version: str) -> bool
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/negotiation.py#L51)

True when an Ananke Plexus version falls inside `SUPPORTED_ANANKE`.

## `guage_kit.harness.catalogue`

Ananke's agent evaluators as Guage Kit metrics.

Ananke Plexus ships evaluators across nine agent-quality dimensions (outcome, trajectory, tool use, planning,
retrieval, safety, resilience, efficiency, multi-agent, architecture). This catalogue discovers them in the
installed harness, so a newer Ananke brings new evaluators without a Guage Kit release, and registers each as a
metric named by its Ananke id (`ananke.trajectory.loop_detection`).

Constructor arguments (an evaluator's configuration) are resolved in this order:

1. metric parameters (`params` in code or `guage.yaml`);
2. the sample's `metadata.ananke` mapping (per-sample configuration);
3. sample fields: an expected trajectory, required or allowed tools come from `expected_tool_calls`, the optimal
   step count from its length, and any other argument from `metadata.<argument>`.

An evaluator whose required arguments can't be resolved skips the sample and says which argument is missing.

### `AnankeEvaluator`

```python
class AnankeEvaluator(
    id: str,
    cls: type,
    dimension: str,
    deterministic: bool,
    description: str,
    params: dict[str, Any] = <factory>,
    annotations: dict[str, str] = <factory>,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/catalogue.py#L39)

AnankeEvaluator(id: 'str', cls: 'type', dimension: 'str', deterministic: 'bool', description: 'str', params: 'dict[str, Any]' = <factory>, annotations: 'dict[str, str]' = <factory>)


### `discover`

```python
discover() -> dict[str, AnankeEvaluator]
```

Every evaluator class in the installed `ananke.plexus.evals.evaluators` package.

### `register_all`

```python
register_all() -> int
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/catalogue.py#L205)

Register every discovered Ananke evaluator in the metric registry (idempotent). Returns the count.

### `run_evaluator`

```python
run_evaluator(
    ev_id: str,
    sample: Sample,
    config: dict[str, Any] | None = None,
    project_root: Path | None = None,
) -> Score
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/catalogue.py#L131)

Score one sample with one Ananke evaluator.

## `guage_kit.harness.convert`

Conversions between Guage Kit's model and Ananke's canonical eval model.

- a `guage_kit.core.sample.Sample` becomes an Ananke `EvalCase` and `AgentTrace` (a recorded trace is
  normalised by Ananke; otherwise one is built from the sample's tool calls, contexts, output and usage);
- a `guage_kit.core.results.RunResult` becomes an Ananke `EvalReport` with one `EvalScore` per metric
  and a gate decision from Ananke's policy engine, and can be written as an Ananke evidence bundle.

### `gate`

```python
gate(run: RunResult, rules: list[GateRule]) -> GateResult
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/convert.py#L176)

Decide PASS/WARN/REVIEW/BLOCK with Ananke's policy engine over the run's metric values.

### `to_case`

```python
to_case(sample: Sample) -> EvalCase
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/convert.py#L35)

Convert a sample into an Ananke Plexus `EvalCase` (input, expected output, and metadata including
relevant document ids).

### `to_policy`

```python
to_policy(rules: list[GateRule]) -> GatePolicy
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/convert.py#L128)

Convert gate rules into an Ananke Plexus `GatePolicy` (minimum, maximum and on-failure level per metric).

### `to_report`

```python
to_report(run: RunResult, rules: list[GateRule] | None = None) -> EvalReport
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/convert.py#L223)

Convert a run into an Ananke Plexus `EvalReport` (scores plus the gate decision) for evidence bundles.

### `to_scores`

```python
to_scores(run: RunResult, rules: list[GateRule] | None = None) -> list[EvalScore]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/convert.py#L138)

Convert a run's metric summaries into Ananke Plexus `EvalScore` records, marking each as passed,
failed or skipped against its gate rule.

### `to_trace`

```python
to_trace(sample: Sample) -> AgentTrace
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/convert.py#L49)

Build an Ananke Plexus `AgentTrace` for a sample: its recorded `trace` when present (normalised), or
a trace assembled from its tool calls, contexts, usage and output.

### `tool_calls_from_trace`

```python
tool_calls_from_trace(sample: Sample) -> list[ToolCall]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/convert.py#L110)

The tool calls of a sample: its own list, or the TOOL spans of its trace.

### `write_evidence`

```python
write_evidence(
    run: RunResult,
    project_root: str | Path = '.',
    rules: list[GateRule] | None = None,
) -> Path
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/harness/convert.py#L260)

Write the run as an Ananke evidence bundle: `.ananke/evidence/<run_id>/eval/` (scores, decision, reports).
