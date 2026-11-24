"""Agent metrics and the Ananke bridge: catalogue, argument resolution, conversions, policy gate, evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guage_kit.core.results import GateRule
from guage_kit.core.sample import Sample, ToolCall
from guage_kit.errors import GuageError
from guage_kit.harness import catalogue, convert, negotiation
from guage_kit.runner.evaluate import evaluate
from tests.conftest import score

EXP = [
    ToolCall(name="lookup_order", arguments={"order_id": "42"}),
    ToolCall(name="issue_refund", arguments={"order_id": "42", "reason": "damaged"}),
]


def test_tool_metrics() -> None:
    perfect = dict(tool_calls=EXP, expected_tool_calls=EXP)
    assert score("tool_call_f1", **perfect) == 1.0
    assert score("tool_calls_exact", **perfect) == 1.0
    skipped = dict(tool_calls=EXP[1:], expected_tool_calls=EXP)
    assert score("tool_call_f1", **skipped) == pytest.approx(2 * 1 * 0.5 / 1.5)
    assert score("tool_sequence_match", **skipped) == pytest.approx(0.5)
    wrong_arg = [
        EXP[0],
        ToolCall(name="issue_refund", arguments={"order_id": "42", "reason": "other"}),
    ]
    assert score(
        "tool_args_accuracy", tool_calls=wrong_arg, expected_tool_calls=EXP
    ) == pytest.approx(0.75)
    retried = [ToolCall(name="lookup_order", arguments={"order_id": "42"}, error="timeout"), *EXP]
    assert score("tool_error_rate", tool_calls=retried) == pytest.approx(1 / 3)
    assert score("redundant_tool_calls", tool_calls=retried) == pytest.approx(1 / 3)
    assert score("goal_success", metadata={"success": True}) == 1.0


def test_tool_calls_come_from_a_recorded_trace() -> None:
    trace = {
        "spans": [
            {
                "span_id": "1",
                "kind": "tool",
                "name": "lookup_order",
                "input": {"order_id": "42"},
                "start_time": "2026-01-01T00:00:00+00:00",
            }
        ]
    }
    assert score("tool_call_f1", trace=trace, expected_tool_calls=EXP[:1]) == 1.0


def test_negotiation_matches_pyproject() -> None:
    import tomllib

    deps = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"][
        "dependencies"
    ]
    ananke = next(d for d in deps if d.startswith("ananke-plexus"))
    assert ananke == "ananke-plexus" + negotiation.SUPPORTED_ANANKE
    h = negotiation.check()
    assert h["compatible"], h["reasons"]
    assert (
        negotiation.supported("0.3.46")
        and not negotiation.supported("0.4.0")
        and not negotiation.supported("0.3.45")
    )


def test_catalogue_discovers_ananke_evaluators() -> None:
    found = catalogue.discover()
    assert len(found) >= 70
    dims = {e.dimension for e in found.values()}
    assert {"trajectory", "tool_use", "safety", "efficiency", "planning"} <= dims
    assert found["ananke.trajectory.strict"].required == ["expected"]


def test_ananke_arguments_resolve_from_params_metadata_and_expected_calls() -> None:
    s = Sample(id="x", tool_calls=EXP, expected_tool_calls=EXP)
    assert (
        catalogue.run_evaluator("ananke.trajectory.strict", s).value == 1.0
    )  # list from expected calls
    assert (
        catalogue.run_evaluator("ananke.trajectory.required_step", s).value == 1.0
    )  # str: the goal action
    denied = catalogue.run_evaluator(
        "ananke.tool_use.tool_denylist", s, {"denied": ["issue_refund"]}
    )
    assert denied.value == 0.0 and denied.passed is False
    meta = Sample(id="y", tool_calls=EXP, metadata={"ananke": {"denied": ["delete_account"]}})
    assert catalogue.run_evaluator("ananke.tool_use.tool_denylist", meta).value == 1.0
    missing = catalogue.run_evaluator(
        "ananke.tool_use.tool_allowlist", Sample(id="z", tool_calls=EXP)
    )
    assert missing.skipped and "allowed" in (missing.reason or "")
    with pytest.raises(GuageError) as e:
        catalogue.run_evaluator("ananke.nope", s)
    assert e.value.code == "GK-HARNESS-002"


def test_ananke_metrics_run_inside_evaluate() -> None:
    loop = [ToolCall(name="search", arguments={"q": str(i)}) for i in range(5)]
    run = evaluate(
        [Sample(id="a", tool_calls=loop), Sample(id="b", tool_calls=EXP)],
        [{"name": "ananke.trajectory.loop_detection", "params": {"max_consecutive": 2}}],
    )
    assert run.summaries["ananke.trajectory.loop_detection"].value == pytest.approx(0.5)


def test_trace_synthesis_and_conversion() -> None:
    s = Sample(
        id="x",
        input="q",
        output="a",
        contexts=["c1"],
        tool_calls=EXP,
        latency_ms=12.0,
        relevant_ids=["d"],
    )
    t = convert.to_trace(s)
    assert [sp.name for sp in t.spans] == ["retrieve", "lookup_order", "issue_refund"]
    assert t.usage.tool_calls == 2 and t.usage.duration_ms == 12
    case = convert.to_case(s)
    assert case.metadata["relevant_docs"] == ["d"]


def test_gate_is_decided_by_ananke_policy(rag_samples: list[Sample]) -> None:
    run = evaluate(
        rag_samples,
        ["faithfulness", "mrr"],
        gates=[
            {"metric": "faithfulness", "min": 0.9},
            {"metric": "mrr", "min": 0.99, "on_fail": "warn"},
        ],
    )
    assert run.gate is not None and run.gate.verdict == "BLOCK"
    assert any("faithfulness" in e for e in run.gate.evidence)
    warn_only = evaluate(
        rag_samples, ["mrr"], gates=[{"metric": "mrr", "min": 0.99, "on_fail": "warn"}]
    )
    assert warn_only.gate and warn_only.gate.verdict == "WARN"
    review = evaluate(
        rag_samples, ["mrr"], gates=[{"metric": "mrr", "min": 0.99, "on_fail": "review"}]
    )
    assert review.gate and review.gate.verdict == "REVIEW"
    ok = evaluate(rag_samples, ["mrr"], gates=[{"metric": "mrr", "min": 0.1}])
    assert ok.gate and ok.gate.verdict == "PASS"


def test_a_gate_on_a_metric_without_value_never_passes(rag_samples: list[Sample]) -> None:
    run = evaluate(rag_samples, ["mrr"], gates=[{"metric": "not_computed", "min": 0.5}])
    assert run.gate and run.gate.verdict == "BLOCK"


def test_evidence_bundle(tmp_path: Path, rag_samples: list[Sample]) -> None:
    run = evaluate(
        rag_samples,
        ["faithfulness", "token_f1"],
        gates=[{"metric": "faithfulness", "min": 0.9}],
        evidence=True,
        project_root=tmp_path,
    )
    d = tmp_path / ".ananke" / "evidence" / run.run_id / "eval"
    scores = json.loads((d / "scores.json").read_text(encoding="utf-8"))
    assert {s["metric"] for s in scores} == {"faithfulness", "token_f1"}
    assert (
        json.loads((d / "policy-decision.json").read_text(encoding="utf-8"))["verdict"] == "BLOCK"
    )
    assert (d / "reports" / "junit.xml").exists() and (d / "manifest.json").exists()
    report = convert.to_report(run, [GateRule(metric="faithfulness", min=0.9)])
    assert report.gate_decision is not None and report.gate_decision.blocks
