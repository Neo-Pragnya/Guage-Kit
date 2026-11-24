"""Conversions between Guage Kit's model and Ananke's canonical eval model.

- a :class:`~guage_kit.core.sample.Sample` becomes an Ananke ``EvalCase`` and ``AgentTrace`` (a recorded trace is
  normalised by Ananke; otherwise one is built from the sample's tool calls, contexts, output and usage);
- a :class:`~guage_kit.core.results.RunResult` becomes an Ananke ``EvalReport`` with one ``EvalScore`` per metric
  and a gate decision from Ananke's policy engine, and can be written as an Ananke evidence bundle.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ananke.plexus.evals.models import (
    AgentSpan,
    AgentTrace,
    EvalCase,
    EvalReport,
    EvalScore,
    EvalStatus,
    GatePolicy,
    SpanKind,
)
from ananke.plexus.evals.models import Usage as AnankeUsage
from ananke.plexus.evals.models.suite import GatePolicyRule
from ananke.plexus.evals.traces.normalize import normalize_trace

from guage_kit.core.results import GateCheck, GateResult, GateRule, RunResult
from guage_kit.core.sample import Sample, ToolCall

_EPOCH = datetime(2025, 1, 1, tzinfo=UTC)


def to_case(sample: Sample) -> EvalCase:
    meta = dict(sample.metadata)
    if sample.relevant_ids and "relevant_docs" not in meta:
        meta["relevant_docs"] = list(sample.relevant_ids)
    expected: Any = sample.expected
    if expected is None and sample.references:
        expected = sample.references[0]
    return EvalCase(
        id=sample.id, input=sample.input, expected=expected, metadata=meta, tags=list(sample.tags)
    )


def to_trace(sample: Sample) -> AgentTrace:
    if sample.trace:
        raw = dict(sample.trace)
        raw.setdefault("trace_id", sample.id)
        raw.setdefault("final_output", sample.output)
        return normalize_trace(raw, runtime=str(raw.get("runtime") or "generic"))
    spans: list[AgentSpan] = []
    t = _EPOCH
    if sample.contexts:
        spans.append(
            AgentSpan(
                span_id="retrieval-0",
                kind=SpanKind.RETRIEVAL,
                name="retrieve",
                started_at=t,
                ended_at=t + timedelta(milliseconds=1),
                input=sample.input,
                output=list(sample.contexts),
            )
        )
    for i, call in enumerate(sample.tool_calls):
        t = t + timedelta(milliseconds=10)
        attrs: dict[str, Any] = {"arguments": call.arguments}
        if call.error:
            attrs["error"] = call.error
            attrs["status"] = "error"
        spans.append(
            AgentSpan(
                span_id=f"tool-{i}",
                kind=SpanKind.TOOL,
                name=call.name,
                started_at=t,
                ended_at=t + timedelta(milliseconds=5),
                input=call.arguments,
                output=call.output,
                attributes=attrs,
                events=[{"name": "error", "message": call.error}] if call.error else [],
            )
        )
    usage = AnankeUsage(
        prompt_tokens=sample.usage.prompt_tokens if sample.usage else None,
        completion_tokens=sample.usage.completion_tokens if sample.usage else None,
        total_tokens=sample.usage.tokens if sample.usage else None,
        cost_usd=sample.usage.cost_usd if sample.usage else None,
        duration_ms=int(sample.latency_ms) if sample.latency_ms is not None else None,
        tool_calls=len(sample.tool_calls),
    )
    return AgentTrace(
        trace_id=sample.id,
        run_id=sample.id,
        runtime="guage-kit",
        model=sample.metadata.get("model"),
        spans=spans,
        final_output=sample.output,
        usage=usage,
        dataset_case_id=sample.id,
    )


def tool_calls_from_trace(sample: Sample) -> list[ToolCall]:
    """The tool calls of a sample: its own list, or the TOOL spans of its trace."""
    if sample.tool_calls or not sample.trace:
        return list(sample.tool_calls)
    trace = to_trace(sample)
    calls = []
    for s in trace.spans_by_kind(SpanKind.TOOL):
        args = s.input if isinstance(s.input, dict) else (s.attributes.get("arguments") or {})
        err = s.attributes.get("error")
        calls.append(
            ToolCall(
                name=s.name, arguments=dict(args), output=s.output, error=str(err) if err else None
            )
        )
    return calls


# ── results → Ananke ─────────────────────────────────────────────────────────────────────────────────────────────
def to_policy(rules: list[GateRule]) -> GatePolicy:
    return GatePolicy(
        rules={
            r.metric: GatePolicyRule(minimum=r.min, maximum=r.max, on_failure=r.on_fail)
            for r in rules
        }
    )


def to_scores(run: RunResult, rules: list[GateRule] | None = None) -> list[EvalScore]:
    by_metric = {r.metric: r for r in rules or []}
    scores: list[EvalScore] = []
    for name, s in run.summaries.items():
        rule = by_metric.get(name)
        status = EvalStatus.SKIPPED if s.value is None else EvalStatus.PASS
        if rule and s.value is not None:
            ok = (rule.min is None or s.value >= rule.min) and (
                rule.max is None or s.value <= rule.max
            )
            status = EvalStatus.PASS if ok else EvalStatus.FAIL
        normalized = s.value if s.value is not None and 0.0 <= s.value <= 1.0 else None
        scores.append(
            EvalScore(
                evaluator_id=f"guage-kit.{s.family or 'metric'}.{name}",
                dimension=s.family or "metric",
                metric=name,
                value=s.value,
                normalized_score=normalized,
                status=status,
                threshold=(
                    rule.min if rule and rule.min is not None else rule.max if rule else None
                ),
                reason=f"n={s.n}"
                + (
                    f", 95% CI [{s.ci_low:.3f}, {s.ci_high:.3f}]"
                    if s.ci_low is not None and s.ci_high is not None
                    else ""
                ),
                deterministic=not s.details.get("judge", False),
                extra={"level": s.level, "skipped": s.skipped, "errors": s.errors},
            )
        )
    return scores


def gate(run: RunResult, rules: list[GateRule]) -> GateResult:
    """Decide PASS/WARN/REVIEW/BLOCK with Ananke's policy engine over the run's metric values."""
    from ananke.plexus.evals.policy.decisions import apply_gate_policy

    scores = [s for s in to_scores(run, rules) if s.metric in {r.metric for r in rules}]
    decision = apply_gate_policy(run.name or "guage-kit", run.run_id, scores, to_policy(rules))
    checks: list[GateCheck] = []
    evidence = list(decision.evidence)
    for rule in rules:
        value = run.value(rule.metric)
        if value is None:
            checks.append(
                GateCheck(
                    metric=rule.metric,
                    value=None,
                    rule=rule,
                    ok=False,
                    message="no value (metric not computed or every sample skipped)",
                )
            )
            evidence.append(f"{rule.metric}: no value")
            continue
        ok = (rule.min is None or value >= rule.min) and (rule.max is None or value <= rule.max)
        bound = []
        if rule.min is not None:
            bound.append(f"≥ {rule.min:g}")
        if rule.max is not None:
            bound.append(f"≤ {rule.max:g}")
        checks.append(
            GateCheck(
                metric=rule.metric,
                value=value,
                rule=rule,
                ok=ok,
                message=f"{value:.4g} {'meets' if ok else 'misses'} {' and '.join(bound)}",
            )
        )
    verdict = decision.verdict.value
    # a rule whose metric produced no value never passes silently
    order = ["PASS", "WARN", "REVIEW", "BLOCK"]
    level = {"block": "BLOCK", "review": "REVIEW", "warn": "WARN"}
    for c in checks:
        if c.value is None and order.index(level[c.rule.on_fail]) > order.index(verdict):
            verdict = level[c.rule.on_fail]
    return GateResult(verdict=verdict, checks=checks, evidence=evidence)  # type: ignore[arg-type]


def to_report(run: RunResult, rules: list[GateRule] | None = None) -> EvalReport:
    from ananke.plexus.evals.models.report import EvalGateDecision, GateVerdict

    scores = to_scores(run, rules)
    decision = None
    if run.gate is not None:
        decision = EvalGateDecision(
            verdict=GateVerdict(run.gate.verdict),
            suite_id=run.name or "guage-kit",
            run_id=run.run_id,
            blocking_dimensions=[
                c.metric for c in run.gate.checks if not c.ok and c.rule.on_fail == "block"
            ],
            warning_dimensions=[
                c.metric for c in run.gate.checks if not c.ok and c.rule.on_fail == "warn"
            ],
            review_dimensions=[
                c.metric for c in run.gate.checks if not c.ok and c.rule.on_fail == "review"
            ],
            evidence=run.gate.evidence,
            decided_at=datetime.now(tz=UTC),
        )
    return EvalReport(
        run_id=run.run_id,
        suite_id=run.name or "guage-kit",
        scores=scores,
        gate_decision=decision,
        summary={
            "dataset": run.dataset,
            "samples": len(run.samples),
            "metrics": {k: v.value for k, v in run.summaries.items()},
            "producer": "guage-kit",
        },
    )


def write_evidence(
    run: RunResult, project_root: str | Path = ".", rules: list[GateRule] | None = None
) -> Path:
    """Write the run as an Ananke evidence bundle: ``.ananke/evidence/<run_id>/eval/`` (scores, decision, reports)."""
    from ananke.plexus.evals.runner import save_eval_evidence

    report = to_report(run, rules)
    return save_eval_evidence(report, Path(project_root) / ".ananke" / "evidence")


__all__ = [
    "gate",
    "to_case",
    "to_policy",
    "to_report",
    "to_scores",
    "to_trace",
    "tool_calls_from_trace",
    "write_evidence",
]
