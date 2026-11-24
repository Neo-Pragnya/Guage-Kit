"""Regression tests for issues found while documenting and acceptance-testing."""

from __future__ import annotations

from pathlib import Path

from guage_kit.config import Suite, run_suite
from guage_kit.core.dataset import Dataset
from guage_kit.core.sample import Sample
from guage_kit.runner import auto_metrics, compare, evaluate


def test_csv_and_tsv_round_trip(tmp_path: Path) -> None:
    ds = Dataset(
        [
            Sample(
                id="1", input="q, with comma", output="a", contexts=["c1", "c2"], metadata={"k": 1}
            )
        ]
    )
    for ext in (".csv", ".tsv"):
        back = Dataset.load(ds.save(tmp_path / f"d{ext}"))
        assert back[0].contexts == ["c1", "c2"] and back[0].input == "q, with comma"


def test_system_prompt_leakage_is_auto_selected() -> None:
    assert "system_prompt_leakage" in auto_metrics(
        [Sample(id="1", output="x", metadata={"system_prompt": "be nice"})]
    )


def test_missing_value_rules_use_their_own_level() -> None:
    samples = [Sample(id="1", output="a", expected="a")]
    assert (
        evaluate(
            samples, ["token_f1"], gates=[{"metric": "nope", "min": 1, "on_fail": "review"}]
        ).gate.verdict
        == "REVIEW"
    )  # type: ignore[union-attr]
    assert (
        evaluate(
            samples, ["token_f1"], gates=[{"metric": "nope", "min": 1, "on_fail": "warn"}]
        ).gate.verdict
        == "WARN"
    )  # type: ignore[union-attr]


def test_corpus_metric_changes_are_not_called_significant() -> None:
    a = evaluate(
        [Sample(id=str(i), output="a b", expected="a b", latency_ms=100) for i in range(5)],
        ["latency_p95"],
    )
    b = evaluate(
        [Sample(id=str(i), output="a b", expected="a b", latency_ms=200) for i in range(5)],
        ["latency_p95"],
    )
    assert compare(a, b).metrics["latency_p95"].direction == "changed"


def test_judge_options_may_set_cache_dir(tmp_path: Path) -> None:
    Dataset([Sample(id="1", output="a", expected="a")]).save(tmp_path / "d.jsonl")
    s = Suite(
        dataset=str(tmp_path / "d.jsonl"),
        metrics=["token_f1"],
        judge="python:tests.targets:upper",
        judge_options={"cache_dir": str(tmp_path / "jc")},
    )
    run, _ = run_suite(s, overrides={"save": False})
    assert run.summaries["token_f1"].value == 1.0


def test_string_judge_caches_under_project_root(tmp_path: Path) -> None:
    calls = []

    import tests.targets as t

    t.judge_reply = lambda system, prompt: calls.append(1) or '{"score": 5, "reasoning": "ok"}'  # type: ignore[attr-defined]
    evaluate(
        [Sample(id="1", output="a")],
        ["judge"],
        judge="python:tests.targets:judge_reply",
        project_root=tmp_path,
    )
    assert list((tmp_path / ".guage" / "cache" / "judge").rglob("*.json"))
