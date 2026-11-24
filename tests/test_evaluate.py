from __future__ import annotations

import json
from pathlib import Path

import pytest

import guage_kit as gk
from guage_kit.core.dataset import Dataset
from guage_kit.core.sample import Sample
from guage_kit.errors import GuageError
from guage_kit.runner import RunStore, auto_metrics, compare, evaluate


def test_dataset_loading_aliases_and_formats(tmp_path: Path) -> None:
    rows = [
        {
            "id": 1,
            "question": "Q?",
            "answer": "A",
            "ground_truth": "A",
            "retrieved_contexts": ["c"],
            "difficulty": "easy",
        }
    ]
    for ext in (".jsonl", ".json", ".yaml"):
        p = tmp_path / f"d{ext}"
        if ext == ".jsonl":
            p.write_text("\n".join(json.dumps(r) for r in rows))
        elif ext == ".json":
            p.write_text(json.dumps({"samples": rows}))
        else:
            import yaml

            p.write_text(yaml.safe_dump(rows))
        ds = Dataset.load(p)
        s = ds[0]
        assert (s.id, s.input, s.output, s.expected, s.contexts, s.metadata["difficulty"]) == (
            "1",
            "Q?",
            "A",
            "A",
            ["c"],
            "easy",
        )
    csv = tmp_path / "d.csv"
    csv.write_text('id,question,answer,contexts,relevant_ids\n1,Q?,A,"[""c1"",""c2""]",a|b\n')
    s = Dataset.load(csv)[0]
    assert s.contexts == ["c1", "c2"] and s.relevant_ids == ["a", "b"]


def test_dataset_errors(tmp_path: Path) -> None:
    with pytest.raises(GuageError) as e:
        Dataset.load(tmp_path / "missing.jsonl")
    assert e.value.code == "GK-DATA-001"
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"id": 1}\n{oops\n')
    with pytest.raises(GuageError) as e:
        Dataset.load(bad)
    assert e.value.code == "GK-DATA-003" and "bad.jsonl:2" in e.value.message
    with pytest.raises(GuageError):
        Dataset([Sample(id="a"), Sample(id="a")])
    with pytest.raises(GuageError) as e:
        Dataset.load(tmp_path / "x.parquet") if (tmp_path / "x.parquet").write_text(
            ""
        ) is not None else None
    assert e.value.code == "GK-DATA-002"


def test_dataset_fingerprint_split_sample_roundtrip(tmp_path: Path) -> None:
    ds = Dataset([Sample(id=str(i), input=f"q{i}", output="a") for i in range(10)], name="t")
    a, b = ds.split(0.3, seed=1)
    assert len(a) == 3 and len(b) == 7 and not ({s.id for s in a} & {s.id for s in b})
    assert ds.sample(4, seed=2).fingerprint == ds.sample(4, seed=2).fingerprint
    p = ds.save(tmp_path / "out.jsonl")
    assert Dataset.load(p).fingerprint == ds.fingerprint
    changed = ds.map(lambda s: s.model_copy(update={"output": "b"}))
    assert (
        changed.fingerprint != ds.fingerprint and changed.input_fingerprint == ds.input_fingerprint
    )


def test_auto_metrics_choose_by_fields(rag_samples: list[Sample]) -> None:
    m = auto_metrics(rag_samples)
    assert {"faithfulness", "context_recall", "mrr", "token_f1"} <= set(m)
    cls = [Sample(id=str(i), input="t", expected="a", label="a", confidence=0.9) for i in range(4)]
    assert {"accuracy", "f1", "ece"} <= set(auto_metrics(cls)) and "token_f1" not in auto_metrics(
        cls
    )


def test_target_callable_dict_and_errors() -> None:
    def rag(question: str) -> dict:
        if "boom" in question:
            raise RuntimeError("model down")
        return {
            "answer": f"echo {question}",
            "contexts": ["echo ctx"],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        }

    data = [Sample(id="1", input="hello"), Sample(id="2", input="boom")]
    run = evaluate(data, ["total_tokens", "faithfulness"], target=rag)
    r1, r2 = run.samples
    assert r1.output == "echo hello" and r1.latency_ms is not None
    assert r2.target_error and "model down" in r2.target_error
    assert run.summaries["total_tokens"].value == 5 and run.summaries["total_tokens"].n == 1
    assert any("failed on 1 of 2" in n for n in run.notes)


def test_target_receiving_sample_and_repeats() -> None:
    calls = {"n": 0}

    def t(sample: Sample) -> str:
        calls["n"] += 1
        return "yes" if calls["n"] % 2 else "yes indeed"

    run = evaluate([Sample(id="1", input="q", expected="yes")], ["token_f1"], target=t, repeats=3)
    assert calls["n"] == 3
    assert (
        run.summaries["self_consistency"].value is not None
        and run.summaries["self_consistency"].value < 1
    )
    assert len(run.samples[0].repeats) == 3


def test_target_by_import_path() -> None:
    run = evaluate([Sample(id="1", input="abc")], ["word_count"], target="tests.targets:upper")
    assert run.samples[0].output == "ABC"
    with pytest.raises(GuageError) as e:
        evaluate([Sample(id="1", input="x")], ["word_count"], target="tests.targets:nope")
    assert e.value.code == "GK-TARGET-001"


def test_summaries_ci_slices_thresholds(rag_samples: list[Sample]) -> None:
    run = evaluate(
        rag_samples,
        [{"name": "token_f1", "threshold": 0.5}, "bleu", "accuracy"],
        slices=["tags", "difficulty"],
    )
    s = run.summaries["token_f1"]
    assert s.ci_low is not None and s.ci_low <= s.value <= s.ci_high  # type: ignore[operator]
    assert s.pass_rate is not None and len(s.histogram) == 10
    assert "difficulty=easy" in run.slices and "tags=geo" in run.slices
    assert run.slices["difficulty=easy"]["token_f1"].n == 2
    assert run.summaries["bleu"].level == "corpus"


def test_metric_errors() -> None:
    with pytest.raises(GuageError) as e:
        evaluate([Sample(id="1", output="a")], ["tokn_f1"])
    assert e.value.code == "GK-METRIC-001" and "token_f1" in (e.value.hint or "")
    with pytest.raises(GuageError) as e:
        evaluate([Sample(id="1", output="a")], [{"name": "rouge", "params": {"nope": 1}}])
    assert e.value.code == "GK-METRIC-002"
    with pytest.raises(GuageError):
        evaluate([Sample(id="1", output="a")], ["recall@x"])
    with pytest.raises(GuageError):
        evaluate([], ["token_f1"])


def test_custom_metric_and_exception_isolation() -> None:
    @gk.metric("shouty_test_metric", family="custom", requires=("output",))
    def shouty(sample: Sample, *, ratio: float = 0.5) -> float:
        if sample.output_text == "crash":
            raise ValueError("bad")
        letters = [c for c in sample.output_text if c.isalpha()]
        return float(sum(c.isupper() for c in letters) / len(letters) >= ratio)

    run = evaluate(
        [Sample(id="1", output="HELLO"), Sample(id="2", output="crash")], ["shouty_test_metric"]
    )
    assert (
        run.summaries["shouty_test_metric"].value == 1.0
        and run.summaries["shouty_test_metric"].errors == 1
    )
    assert "ValueError" in (run.samples[1].scores["shouty_test_metric"].error or "")


def test_store_compare_and_regressions(tmp_path: Path) -> None:
    base = [
        Sample(id=str(i), input="q", output="the right answer", expected="the right answer")
        for i in range(30)
    ]
    worse = [s.model_copy(update={"output": "wrong" if int(s.id) < 20 else s.output}) for s in base]
    a = evaluate(base, ["token_f1"], save=True, project_root=tmp_path, name="a")
    b = evaluate(worse, ["token_f1"], save=True, project_root=tmp_path, name="b")
    store = RunStore(tmp_path / ".guage" / "runs")
    assert len(store.list()) == 2
    c = compare(store.load(a.run_id), b)
    d = c.metrics["token_f1"]
    assert d.direction == "regressed" and d.delta == pytest.approx(-20 / 30) and d.losses == 20
    assert c.same_data and c.regressions[0].metric == "token_f1"
    store.set_baseline(a.run_id, "main")
    assert store.load("baseline:main").run_id == a.run_id
    with pytest.raises(GuageError):
        store.load("baseline:nope")
    with pytest.raises(GuageError):
        compare(a, evaluate([Sample(id="other", output="x", expected="x")], ["token_f1"]))


def test_pairwise_compare_with_judge() -> None:
    from guage_kit.runner.compare import pairwise

    a = evaluate(
        [
            Sample(
                id=str(i),
                input="Capital of France?",
                output="Berlin.",
                expected="Paris is the capital.",
            )
            for i in range(6)
        ],
        ["token_f1"],
    )
    b = evaluate(
        [
            Sample(
                id=str(i),
                input="Capital of France?",
                output="Paris is the capital.",
                expected="Paris is the capital.",
            )
            for i in range(6)
        ],
        ["token_f1"],
    )
    res = pairwise(a, b, "heuristic", criterion="correctness")
    assert res["b_wins"] == 6 and res["win_rate"] == 1.0


def test_suite_config_and_baseline_regression_gate(tmp_path: Path) -> None:
    from guage_kit.config import load_suite, run_suite

    data = tmp_path / "data.jsonl"
    Dataset(
        [
            Sample(id=str(i), input="q", output="right answer", expected="right answer")
            for i in range(20)
        ]
    ).save(data)
    (tmp_path / "guage.yaml").write_text(
        "name: t\ndataset: data.jsonl\nmetrics: [token_f1]\ngates:\n  - {metric: token_f1, min: 0.5}\n  - {metric: token_f1, max_drop: 0.05}\nreports: {html: out/r.html, junit: out/j.xml, markdown: out/s.md, json: out/run.json}\n"
    )
    s = load_suite(tmp_path / "guage.yaml")
    run, cmp = run_suite(s)
    assert run.gate and run.gate.verdict == "PASS" and cmp is None
    for f in ("r.html", "j.xml", "s.md", "run.json"):
        assert (tmp_path / "out" / f).exists()
    RunStore(tmp_path / ".guage" / "runs").set_baseline(run.run_id, "main")
    Dataset(
        [
            Sample(
                id=str(i),
                input="q",
                output="right" if i < 10 else "right answer",
                expected="right answer",
            )
            for i in range(20)
        ]
    ).save(data)
    s2 = load_suite(tmp_path / "guage.yaml")
    s2.baseline = "baseline:main"
    run2, cmp2 = run_suite(s2)
    assert cmp2 is not None and run2.gate and run2.gate.verdict == "BLOCK"
    assert any("dropped" in e for e in run2.gate.evidence)


def test_suite_validation(tmp_path: Path) -> None:
    from guage_kit.config import load_suite

    (tmp_path / "g.yaml").write_text("dataset: x.jsonl\nmetrix: [a]\n")
    with pytest.raises(GuageError) as e:
        load_suite(tmp_path / "g.yaml")
    assert e.value.code == "GK-CONFIG-001" and "metrix" in e.value.message
