from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from guage_kit.cli import app
from guage_kit.core.dataset import Dataset
from guage_kit.core.sample import Sample
from guage_kit.errors import CODES, GuageError

runner = CliRunner()
ROOT = Path(__file__).parents[1]


def invoke(*args: str) -> object:
    return runner.invoke(app, list(args))


def test_cli_init_run_report_compare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    r = invoke("init")
    assert r.exit_code == 0 and (tmp_path / "guage.yaml").exists()  # type: ignore[attr-defined]
    assert invoke("init").output.startswith("Nothing written")  # type: ignore[attr-defined]
    r = invoke("run", "--json")
    assert r.exit_code == 0, r.output  # type: ignore[attr-defined]
    assert json.loads(r.output)["gate"]["verdict"] in ("PASS", "WARN")  # type: ignore[attr-defined]
    assert (tmp_path / "reports" / "guage-report.html").exists()
    assert invoke("baseline", "set").exit_code == 0  # type: ignore[attr-defined]
    r = invoke("run", "--gate", "token_f1>=0.999", "--no-save")
    assert r.exit_code == 1  # type: ignore[attr-defined]
    assert (
        invoke("run", "--gate", "token_f1>=0.999", "--no-save", "--fail-on", "never").exit_code == 0
    )  # type: ignore[attr-defined]
    r = invoke("compare", "baseline:main", "latest", "-o", "cmp.html", "--json")
    assert r.exit_code == 0 and (tmp_path / "cmp.html").exists()  # type: ignore[attr-defined]
    assert invoke("report", "latest", "-o", "again.html").exit_code == 0  # type: ignore[attr-defined]
    assert "PASS" in invoke("runs").output or "WARN" in invoke("runs").output  # type: ignore[attr-defined]


def test_cli_errors_have_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    r = invoke("run")
    assert r.exit_code == 2 and "GK-CONFIG-001" in r.output  # type: ignore[attr-defined]
    r = invoke("run", "--data", "missing.jsonl")
    assert r.exit_code == 2 and "GK-DATA-001" in r.output  # type: ignore[attr-defined]
    r = invoke("run", "--data", "missing.jsonl", "--gate", "nonsense")
    assert r.exit_code == 2  # type: ignore[attr-defined]
    assert invoke("metrics", "show", "nope").exit_code == 2  # type: ignore[attr-defined]


def test_cli_metrics_data_probe_synth_demo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    items = json.loads(invoke("metrics", "list", "--json").output)  # type: ignore[attr-defined]
    assert len(items) > 150 and any(i["family"].startswith("ananke.") for i in items)
    assert json.loads(invoke("metrics", "show", "bleu").output)["level"] == "corpus"  # type: ignore[attr-defined]
    Dataset(
        [Sample(id=str(i), input=f"Question {i}?", output="a", expected="a") for i in range(6)]
    ).save(tmp_path / "d.jsonl")
    assert "auto_metrics" in json.loads(invoke("data", "stats", "d.jsonl", "--json").output)  # type: ignore[attr-defined]
    assert invoke("data", "validate", "d.jsonl").exit_code == 0  # type: ignore[attr-defined]
    assert (
        invoke("data", "convert", "d.jsonl", "d.yaml").exit_code == 0
        and (tmp_path / "d.yaml").exists()
    )  # type: ignore[attr-defined]
    assert invoke("data", "split", "d.jsonl").exit_code == 0 and (tmp_path / "d.a.jsonl").exists()  # type: ignore[attr-defined]
    assert (
        invoke("probe", "redteam", "-o", "rt.jsonl").exit_code == 0
        and len(Dataset.load(tmp_path / "rt.jsonl")) >= 15
    )  # type: ignore[attr-defined]
    assert invoke("probe", "perturb", "d.jsonl", "-o", "p.jsonl").exit_code == 0  # type: ignore[attr-defined]
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text(
        "Lumen was founded in 2019 in Lisbon. The team has 42 engineers working on sync and search features across Europe.\n"
        * 3,
        encoding="utf-8",
    )
    assert invoke("synth", "docs", "-o", "syn.jsonl", "--corpus", "corpus.jsonl").exit_code == 0  # type: ignore[attr-defined]
    assert len(Dataset.load(tmp_path / "syn.jsonl")) >= 1
    assert (
        invoke("demo", "-o", "demo").exit_code == 0
        and (tmp_path / "demo" / "support-agent.html").exists()
    )  # type: ignore[attr-defined]
    assert invoke("doctor", "--json").exit_code == 0  # type: ignore[attr-defined]
    assert invoke("version").exit_code == 0  # type: ignore[attr-defined]


def test_judge_calibrate_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    Dataset(
        [
            Sample(
                id=str(i),
                input="q",
                output="Paris is the capital" if i % 2 else "Berlin",
                expected="Paris is the capital",
                metadata={"human_score": 5 if i % 2 else 1},
            )
            for i in range(10)
        ]
    ).save(tmp_path / "l.jsonl")
    out = json.loads(invoke("judge", "calibrate", "l.jsonl", "--json").output)  # type: ignore[attr-defined]
    assert out["n"] == 10 and out["quadratic_kappa"] > 0.5


def test_pytest_plugin(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        from guage_kit import Sample

        def test_quality(guage):
            run = guage.evaluate([Sample(id="1", output="Paris", expected="Paris")], ["exact_match"])
            guage.check(run, exact_match=1.0)

        def test_bar_missed(guage):
            run = guage.evaluate([Sample(id="1", output="Lyon", expected="Paris")], ["exact_match"])
            guage.check(run, exact_match=0.5)

        def test_single(guage):
            guage.assert_metric("token_f1", "the capital is Paris", "Paris", minimum=0.3)
            guage.assert_metric("faithfulness", "Paris is in France.", contexts=["Paris is in France."], minimum=1.0)
        """
    )
    result = pytester.runpytest(f"--guage-report={pytester.path / 'rep'}")
    result.assert_outcomes(passed=2, failed=1)
    result.stdout.fnmatch_lines(
        ["*Guage Kit quality bar missed*", "*exact_match = 0, expected >= 0.5*", "*Guage Kit*"]
    )
    assert len(list((pytester.path / "rep").glob("*.html"))) == 2


def test_probes_and_synth_units() -> None:
    from guage_kit.probes import perturb, redteam_dataset, robustness
    from guage_kit.synth import chunk, cloze_dataset

    ds = Dataset(
        [Sample(id="1", input="What is the refund window for annual plans?", contexts=["a", "b"])]
    )
    p = perturb(ds, ["typos", "uppercase", "shuffle_contexts", "drop_top_context", "noise_context"])
    assert {s.metadata["perturbation"] for s in p} == {
        "typos",
        "uppercase",
        "shuffle_contexts",
        "drop_top_context",
        "noise_context",
    }
    res = robustness(
        ds,
        lambda q: "14 days" if "refund" in q.lower() else "?",
        kinds=["uppercase", "filler"],
        metrics=["word_count"],
    )
    assert res["robustness_score"] == 1.0
    rt = redteam_dataset(system_prompt="secret instructions here")
    assert {t for s in rt for t in s.tags} >= {
        "injection",
        "over_refusal",
        "pii_extraction",
        "system_prompt_extraction",
    }
    assert all(s.metadata.get("canary", "GK-CANARY-").startswith("GK-CANARY-") for s in rt)
    chunks = chunk(
        [("doc", "The service opened in 2019 in Lisbon with 42 engineers. " * 10)],
        size=30,
        overlap=5,
    )
    assert chunks and len({c["id"] for c in chunks}) == len(chunks)
    cz = cloze_dataset(chunks)
    assert cz[0].input.startswith("Fill in the blank") and cz[0].relevant_ids


def test_error_codes_are_documented() -> None:
    doc = (ROOT / "docs" / "reference" / "errors.md").read_text(encoding="utf-8")
    for code in CODES:
        assert code in doc, code
    with pytest.raises(ValueError):
        GuageError("GK-NOPE-999", "x")


def test_packaging_metadata_and_licences() -> None:
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert meta["project"]["license"] == "Apache-2.0"
    assert "streamlit" not in json.dumps(meta)
    deps = " ".join(
        meta["project"]["dependencies"]
        + [d for k, v in meta["project"]["optional-dependencies"].items() if k != "dev" for d in v]
    )
    for banned in ("gpl", "agpl"):
        assert banned not in deps.lower()
    from guage_kit.version import __version__

    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
    assert __version__ in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
