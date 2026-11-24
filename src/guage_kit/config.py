"""Suites: an evaluation described in ``guage.yaml``, versioned with your code and run with ``guage run``.

.. code-block:: yaml

    name: support-bot
    dataset: data/support.jsonl
    target: support_bot.pipeline:answer      # optional: module:function or a provider spec
    judge: anthropic:claude-opus-5-5         # or heuristic (offline), ollama:llama3.1, …
    metrics:
      - token_f1
      - recall@5
      - {name: faithfulness, threshold: 0.8}
      - {name: judge, params: {criterion: correctness}, as: judge_correctness}
    slices: [tags, difficulty]
    gates:
      - {metric: faithfulness, min: 0.85}
      - {metric: judge_correctness, min: 0.7, on_fail: warn}
      - {metric: token_f1, max_drop: 0.02}  # versus the baseline
    baseline: baseline:main
    reports: {html: reports/eval.html, junit: reports/eval.xml, markdown: reports/eval.md}
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError

from guage_kit.core.results import GateRule, RunResult
from guage_kit.errors import GuageError


class Reports(BaseModel):
    model_config = ConfigDict(extra="forbid")
    html: str | None = None
    json_: str | None = Field(default=None, alias="json")
    junit: str | None = None
    markdown: str | None = None
    profile: Literal["private", "public"] = "private"


class Suite(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str = "evaluation"
    description: str = ""
    dataset: str
    target: str | None = None
    target_options: dict[str, Any] = Field(default_factory=dict)
    judge: str | None = None
    judge_options: dict[str, Any] = Field(default_factory=dict)
    embedder: str | None = None
    metrics: list[str | dict[str, Any]] | Literal["auto"] = "auto"
    slices: list[str] = Field(default_factory=list)
    gates: list[GateRule] = Field(default_factory=list)
    baseline: str | None = None
    repeats: int = 1
    concurrency: int = 4
    confidence: float = 0.95
    seed: int = 0
    limit: int | None = None
    reports: Reports = Field(default_factory=Reports)
    evidence: bool = False
    _base: str = PrivateAttr(default=".")

    @property
    def base_dir(self) -> Path:
        return Path(self._base)


def load_suite(path: str | Path) -> Suite:
    p = Path(path)
    if not p.is_file():
        raise GuageError(
            "GK-CONFIG-001",
            f"suite file not found: {p}",
            hint="`guage init` writes a starter guage.yaml",
        )
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        suite = Suite.model_validate(data)
    except yaml.YAMLError as exc:
        raise GuageError("GK-CONFIG-001", f"{p.name}: {exc}") from exc
    except ValidationError as exc:
        first = exc.errors()[0]
        where = ".".join(str(x) for x in first["loc"])
        raise GuageError("GK-CONFIG-001", f"{p.name}: {where}: {first['msg']}") from exc
    suite._base = str(p.parent)
    return suite


def run_suite(
    suite: Suite, *, overrides: dict[str, Any] | None = None, progress: Any = None
) -> tuple[RunResult, Any]:
    """Run a suite: evaluate, gate (Ananke), compare with the baseline, write the configured reports.

    Returns ``(run, comparison_or_None)``. A ``max_drop`` rule that the candidate exceeds versus the baseline turns
    the verdict into its ``on_fail`` level.
    """
    from guage_kit.core.dataset import Dataset
    from guage_kit.runner.compare import compare, regression_gate
    from guage_kit.runner.evaluate import evaluate
    from guage_kit.runner.store import RunStore

    o = overrides or {}
    base = suite.base_dir
    dataset_path = Path(suite.dataset)
    if not dataset_path.is_absolute():
        dataset_path = base / dataset_path
    ds = Dataset.load(dataset_path)
    if suite.limit:
        ds = Dataset(ds.samples[: suite.limit], name=ds.name, source=ds.source)
    judge: Any = o.get("judge", suite.judge)
    if isinstance(judge, str) and judge not in ("heuristic", "offline"):
        from guage_kit.judges.judge import LLMJudge

        options = dict(suite.judge_options)
        cache_dir = options.pop("cache_dir", base / ".guage" / "cache" / "judge")
        judge = LLMJudge(judge, cache_dir=cache_dir, **options)
    target: Any = o.get("target", suite.target)
    if isinstance(target, str):
        # `module:function` names the user's own code next to guage.yaml, as `python -m` would see it
        import sys

        for folder in (str(base.resolve()), str(Path.cwd())):
            if folder not in sys.path:
                sys.path.insert(0, folder)
        from guage_kit.runner.target import make_target

        target = make_target(target, **suite.target_options)
    gates = [g for g in suite.gates if g.min is not None or g.max is not None]
    run = evaluate(
        ds,
        None if suite.metrics == "auto" else suite.metrics,
        target=target,
        judge=judge,
        embedder=suite.embedder,
        gates=gates or None,
        slices=suite.slices,
        name=suite.name,
        concurrency=suite.concurrency,
        repeats=suite.repeats,
        confidence=suite.confidence,
        seed=suite.seed,
        save=o.get("save", True),
        evidence=False,
        project_root=base,
        progress=progress,
        config={"suite": suite.model_dump(mode="json", by_alias=True)},
    )
    comparison = None
    baseline = o.get("baseline", suite.baseline)
    if baseline:
        store = RunStore(base / ".guage" / "runs")
        try:
            comparison = compare(store.load(baseline), run)
        except GuageError as exc:
            run.notes.append(f"baseline not compared: {exc.message}")
        if comparison is not None:
            problems = regression_gate(comparison, suite.gates)
            if problems:
                from guage_kit.core.results import GateCheck, GateResult

                order = ["PASS", "WARN", "REVIEW", "BLOCK"]
                gate = run.gate or GateResult(verdict="PASS")
                for rule in suite.gates:
                    msg = next((p for p in problems if p.startswith(rule.metric + " ")), None)
                    if msg:
                        gate.checks.append(
                            GateCheck(
                                metric=rule.metric,
                                value=run.value(rule.metric),
                                rule=rule,
                                ok=False,
                                message=msg,
                            )
                        )
                        gate.evidence.append(msg)
                        level = {"block": "BLOCK", "warn": "WARN", "review": "REVIEW"}[rule.on_fail]
                        if order.index(level) > order.index(gate.verdict):
                            gate.verdict = level  # type: ignore[assignment]
                run.gate = gate
    if suite.evidence:
        from guage_kit.harness.convert import write_evidence

        write_evidence(run, base, suite.gates)
    write_configured_reports(run, suite.reports, base, comparison)
    return run, comparison


def write_configured_reports(
    run: RunResult, reports: Reports, base: Path, comparison: Any = None
) -> dict[str, Path]:
    from guage_kit.reports import junit, markdown, write_report

    out: dict[str, Path] = {}

    def resolve(p: str) -> Path:
        q = Path(p)
        return q if q.is_absolute() else base / q

    if reports.html:
        out["html"] = write_report(
            run, resolve(reports.html), profile=reports.profile, comparison=comparison
        )
    if reports.json_:
        out["json"] = run.save(resolve(reports.json_))
    if reports.junit:
        p = resolve(reports.junit)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(junit(run), encoding="utf-8")
        out["junit"] = p
    if reports.markdown:
        p = resolve(reports.markdown)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(markdown(run, comparison), encoding="utf-8")
        out["markdown"] = p
    return out


STARTER = """# Guage Kit suite. Run it with: guage run
name: {name}
dataset: data/sample.jsonl
# target: my_package.pipeline:answer     # the system under test (module:function or a provider spec)
judge: heuristic                         # offline; for a model judge: anthropic:claude-opus-5-5
metrics: auto                            # or a list, e.g. [token_f1, faithfulness, recall@5]
slices: [tags]
gates:
  - {{metric: faithfulness, min: 0.7}}
  - {{metric: recall@5, min: 0.8, on_fail: warn}}
reports:
  html: reports/guage-report.html
  junit: reports/guage-junit.xml
  markdown: reports/guage-summary.md
"""


__all__ = ["STARTER", "Reports", "Suite", "load_suite", "run_suite", "write_configured_reports"]
