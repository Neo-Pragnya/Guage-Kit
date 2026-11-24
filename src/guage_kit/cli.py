"""The ``guage`` command line. Every command prints for people by default and JSON with ``--json``.

Exit codes: 0 success; 1 the quality gate blocked (or ``--fail-on`` was reached); 2 a usage or data error with a
stable ``GK-*`` code.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from guage_kit.errors import GuageError
from guage_kit.version import __version__

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Guage Kit: measure LLMs, RAG, retrieval, embeddings, classifiers and agents.",
)
metrics_app = typer.Typer(no_args_is_help=True, help="Browse the metric catalogue.")
data_app = typer.Typer(
    no_args_is_help=True, help="Validate, describe, convert, split and sample datasets."
)
judge_app = typer.Typer(no_args_is_help=True, help="Calibrate judges against human labels.")
probe_app = typer.Typer(no_args_is_help=True, help="Robustness and red-team probes.")
baseline_app = typer.Typer(
    no_args_is_help=True, help="Name a run as the baseline to compare against."
)
app.add_typer(metrics_app, name="metrics")
app.add_typer(data_app, name="data")
app.add_typer(judge_app, name="judge")
app.add_typer(probe_app, name="probe")
app.add_typer(baseline_app, name="baseline")

out = Console()
err = Console(stderr=True)


def _version_flag(value: bool) -> None:
    if value:
        print(f"guage-kit {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_flag,
        is_eager=True,
        help="Print the version and exit.",
    ),
) -> None:
    """Guage Kit: measure LLMs, RAG, retrieval, embeddings, classifiers and agents."""


_ORDER = ["PASS", "WARN", "REVIEW", "BLOCK"]
_COLOR = {"PASS": "green", "WARN": "yellow", "REVIEW": "magenta", "BLOCK": "red"}


def _fail(exc: GuageError) -> None:
    err.print(f"[red]error[/red] [bold]{exc.code}[/bold]: {exc.message}")
    if exc.hint:
        err.print(f"[dim]hint: {exc.hint}[/dim]")
    raise typer.Exit(2)


def _fmt(v: float | None) -> str:
    if v is None:
        return "–"
    return f"{v:,.0f}" if abs(v) >= 1000 else f"{v:.3f}"


def _print_run(run: Any) -> None:
    t = Table(
        title=f"{run.name} · {len(run.samples)} samples · run {run.run_id}", title_justify="left"
    )
    for c, j in (
        ("metric", "left"),
        ("value", "right"),
        ("95% CI", "right"),
        ("n", "right"),
        ("pass", "right"),
    ):
        t.add_column(c, justify=j)  # type: ignore[arg-type]
    for s in run.summaries.values():
        ci = f"{_fmt(s.ci_low)} – {_fmt(s.ci_high)}" if s.ci_low is not None else ""
        pr = f"{s.pass_rate:.0%}" if s.pass_rate is not None else ""
        t.add_row(
            f"{s.metric} {'↑' if s.higher_is_better else '↓'}", _fmt(s.value), ci, str(s.n), pr
        )
    out.print(t)
    for n in run.notes:
        out.print(f"[yellow]note:[/yellow] {n}")
    if run.gate:
        out.print(f"Gate: [bold {_COLOR[run.gate.verdict]}]{run.gate.verdict}[/]")
        for c in run.gate.checks:
            out.print(f"  {'[green]✓[/green]' if c.ok else '[red]✕[/red]'} {c.metric}: {c.message}")


def _exit_for(run: Any, fail_on: str) -> None:
    if (
        run.gate
        and fail_on != "never"
        and _ORDER.index(run.gate.verdict) >= _ORDER.index(fail_on.upper())
    ):
        raise typer.Exit(1)


def _parse_gate(text: str) -> dict[str, Any]:
    """Gate rules from the command line, in a shell-safe form or a quoted comparison:

    ``recall@3:min=0.8``, ``latency_p95:max=1200:warn``, ``'faithfulness>=0.8'``, ``'latency_p95<=1200:warn'``.
    """
    hint = "use metric:min=value or metric:max=value (optionally :warn or :review), or quote 'metric>=value'"
    rule: dict[str, Any] = {"on_fail": "block"}
    try:
        if ">=" in text or "<=" in text:
            expr, _, level = text.partition(":")
            op = ">=" if ">=" in expr else "<="
            metric, _, value = expr.partition(op)
            rule.update({"metric": metric.strip(), "min" if op == ">=" else "max": float(value)})
            if level:
                rule["on_fail"] = level
        else:
            metric, *parts = text.split(":")
            rule["metric"] = metric.strip()
            for part in parts:
                key, eq, value = part.partition("=")
                if eq and key in ("min", "max", "max_drop"):
                    rule[key] = float(value)
                elif not eq and part in ("block", "warn", "review"):
                    rule["on_fail"] = part
                else:
                    raise ValueError(part)
    except ValueError as exc:
        raise GuageError("GK-CONFIG-001", f"bad gate {text!r}", hint=hint) from exc
    if (
        not rule.get("metric")
        or not ({"min", "max"} & set(rule))
        or rule["on_fail"] not in ("block", "warn", "review")
    ):
        raise GuageError("GK-CONFIG-001", f"bad gate {text!r}", hint=hint)
    return rule


@app.command()
def version(as_json: bool = typer.Option(False, "--json")) -> None:
    """Print the Guage Kit and Ananke Plexus versions."""
    from guage_kit.harness.negotiation import installed_version

    info = {
        "guage_kit": __version__,
        "ananke_plexus": installed_version(),
        "python": sys.version.split()[0],
    }
    out.print_json(json.dumps(info)) if as_json else out.print(
        f"guage-kit {info['guage_kit']} · ananke-plexus {info['ananke_plexus']} · python {info['python']}"
    )


@app.command()
def doctor(as_json: bool = typer.Option(False, "--json")) -> None:
    """Check the Ananke harness, optional extras and provider credentials (names only, never values)."""
    import importlib.util
    import os

    from guage_kit.harness.negotiation import check

    h = check()
    extras = {
        name: importlib.util.find_spec(mod) is not None
        for name, mod in (
            ("anthropic", "anthropic"),
            ("embeddings", "sentence_transformers"),
            ("jsonschema", "jsonschema"),
            ("bedrock", "boto3"),
        )
    }
    keys = {
        k: bool(os.environ.get(k))
        for k in (
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "GUAGE_OPENAI_COMPATIBLE_KEY",
            "OLLAMA_HOST",
        )
    }
    from guage_kit.metrics import ANANKE_EVALUATORS, REGISTRY

    report = {
        "guage_kit": __version__,
        "harness": h,
        "extras": extras,
        "credentials_present": keys,
        # nosemgrep: python.sqlalchemy.performance.performance-improvements.len-all-count
        "metrics": len(REGISTRY.all()),
        "ananke_evaluators": ANANKE_EVALUATORS,
    }
    if as_json:
        out.print_json(json.dumps(report))
    else:
        ok = "[green]compatible[/green]" if h["compatible"] else "[red]incompatible[/red]"
        out.print(f"Ananke Plexus {h['ananke_version']} ({h['supported_range']}): {ok}")
        for r in h["reasons"]:
            out.print(f"  [red]•[/red] {r}")
        out.print(f"Metrics: {report['metrics']} ({ANANKE_EVALUATORS} from Ananke)")
        out.print("Extras: " + ", ".join(f"{k} {'✓' if v else '–'}" for k, v in extras.items()))
        out.print(
            "Credentials: " + ", ".join(f"{k} {'set' if v else 'unset'}" for k, v in keys.items())
        )
    if not h["compatible"]:
        raise typer.Exit(2)


@app.command()
def init(
    directory: Path = typer.Argument(
        Path("."), help="Where to write guage.yaml and a sample dataset."
    ),
    name: str = typer.Option("my-evaluation", "--name"),
) -> None:
    """Write a starter guage.yaml and data/sample.jsonl (never overwrites)."""
    from guage_kit.config import STARTER
    from guage_kit.demo import rag_dataset

    directory.mkdir(parents=True, exist_ok=True)
    suite = directory / "guage.yaml"
    data = directory / "data" / "sample.jsonl"
    wrote = []
    if not suite.exists():
        suite.write_text(STARTER.format(name=name), encoding="utf-8")
        wrote.append(suite)
    if not data.exists():
        rag_dataset("v2").sample(12).save(data)
        wrote.append(data)
    for p in wrote:
        out.print(f"[green]wrote[/green] {p}")
    if not wrote:
        out.print("Nothing written: guage.yaml and data/sample.jsonl already exist.")
    out.print("Next: [bold]guage run[/bold]  (then open reports/guage-report.html)")


@app.command()
def run(
    suite: Path = typer.Argument(
        None, help="A guage.yaml suite (default: ./guage.yaml when --data is not given)."
    ),
    data: Path = typer.Option(None, "--data", "-d", help="Dataset file (instead of a suite)."),
    metrics: str = typer.Option(
        None, "--metrics", "-m", help="Comma-separated metrics (default: auto)."
    ),
    target: str = typer.Option(
        None, "--target", help="module:function or a provider spec to produce outputs."
    ),
    judge: str = typer.Option(
        None, "--judge", help="heuristic, anthropic:<model>, ollama:<model>, openai:<model> …"
    ),
    gate: list[str] = typer.Option(
        [],
        "--gate",
        "-g",
        help="metric:min=V or metric:max=V (add :warn or :review), or a quoted 'metric>=V'; repeatable.",
    ),
    slice_by: list[str] = typer.Option([], "--slice", help="tags or a metadata key; repeatable."),
    html: Path = typer.Option(None, "--html", help="Write the HTML report here."),
    junit: Path = typer.Option(None, "--junit"),
    markdown: Path = typer.Option(None, "--markdown", "--md"),
    json_out: Path = typer.Option(None, "--json-out", help="Write run.json here."),
    profile: str = typer.Option(
        "private", "--profile", help="private or public (public removes sample text)."
    ),
    baseline: str = typer.Option(
        None, "--baseline", help="Compare with a run id, path or baseline:<name>."
    ),
    repeats: int = typer.Option(None, "--repeats"),
    limit: int = typer.Option(None, "--limit", help="Evaluate only the first N samples."),
    save: bool = typer.Option(True, "--save/--no-save", help="Keep the run under .guage/runs."),
    evidence: bool = typer.Option(
        False, "--evidence", help="Also write an Ananke evidence bundle."
    ),
    fail_on: str = typer.Option(
        "block", "--fail-on", help="Exit 1 at this verdict or worse: warn, review, block or never."
    ),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Run an evaluation from a suite file or from flags, gate it and write reports."""
    from guage_kit.config import Reports, Suite, load_suite, run_suite
    from guage_kit.core.results import GateRule

    try:
        if data is None:
            s = load_suite(suite or Path("guage.yaml"))
        else:
            s = Suite(dataset=str(data.resolve()), name=data.stem)
        if metrics:
            s.metrics = [m.strip() for m in metrics.split(",") if m.strip()]
        if target:
            s.target = target
        if judge:
            s.judge = judge
        if gate:
            s.gates = [GateRule.model_validate(_parse_gate(g)) for g in gate]
        if slice_by:
            s.slices = list(slice_by)
        if repeats:
            s.repeats = repeats
        if limit:
            s.limit = limit
        if evidence:
            s.evidence = True
        cwd = Path.cwd()
        r = s.reports
        s.reports = Reports(
            html=str((cwd / html).resolve()) if html else r.html,
            json=str((cwd / json_out).resolve()) if json_out else r.json_,
            junit=str((cwd / junit).resolve()) if junit else r.junit,
            markdown=str((cwd / markdown).resolve()) if markdown else r.markdown,
            profile=profile if profile != "private" else r.profile,  # type: ignore[arg-type]
        )
        with err.status("evaluating…") if not as_json else _Null():
            result, comparison = run_suite(
                s, overrides={"save": save, **({"baseline": baseline} if baseline else {})}
            )
    except GuageError as exc:
        _fail(exc)
        return
    if as_json:
        out.print_json(result.to_json())
    else:
        _print_run(result)
        if comparison is not None:
            out.print(
                f"Versus baseline: improved {', '.join(comparison.improved) or '–'}; regressed [red]{', '.join(comparison.regressed) or '–'}[/red]"
            )
        for key in ("html", "junit", "markdown", "json_"):
            p = getattr(s.reports, key)
            if p:
                out.print(f"[dim]{key.rstrip('_')}: {p}[/dim]")
    _exit_for(result, fail_on)


class _Null:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *a: Any) -> None:
        return None


@app.command()
def report(
    run_ref: str = typer.Argument("latest", help="Run id, path, latest or baseline:<name>."),
    output: Path = typer.Option(Path("guage-report.html"), "-o", "--output"),
    profile: str = typer.Option("private", "--profile"),
    against: str = typer.Option(None, "--against", help="Include a comparison with this run."),
) -> None:
    """Render the HTML report of a saved run."""
    from guage_kit.reports import write_report
    from guage_kit.runner.compare import compare
    from guage_kit.runner.store import RunStore

    try:
        store = RunStore()
        r = store.load(run_ref)
        cmp = compare(store.load(against), r) if against else None
        p = write_report(r, output, comparison=cmp, profile=profile)
    except GuageError as exc:
        _fail(exc)
        return
    out.print(f"[green]wrote[/green] {p}")


@app.command()
def compare(
    baseline: str = typer.Argument(..., help="Baseline run (id, path, latest~1, baseline:<name>)."),
    candidate: str = typer.Argument("latest", help="Candidate run."),
    output: Path = typer.Option(None, "-o", "--output", help="Write a comparison HTML report."),
    judge: str = typer.Option(
        None, "--judge", help="Also judge outputs head to head with this judge."
    ),
    criterion: str = typer.Option("helpfulness", "--criterion"),
    min_effect: float = typer.Option(0.0, "--min-effect", help="Ignore changes smaller than this."),
    fail_on_regression: bool = typer.Option(
        False, "--fail-on-regression", help="Exit 1 if any metric regressed significantly."
    ),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Compare two runs with paired statistics (bootstrap CI, permutation test, Holm correction)."""
    from guage_kit.reports import write_report
    from guage_kit.runner.compare import compare as _compare
    from guage_kit.runner.compare import pairwise
    from guage_kit.runner.store import RunStore

    try:
        store = RunStore()
        a, b = store.load(baseline), store.load(candidate)
        c = _compare(a, b, min_effect=min_effect)
        if judge:
            c.pairwise = pairwise(a, b, judge, criterion=criterion)
        if output:
            write_report(b, output, comparison=c)
    except GuageError as exc:
        _fail(exc)
        return
    if as_json:
        out.print_json(c.model_dump_json(by_alias=True))
    else:
        t = Table(title=f"{a.name} ({a.run_id}) → {b.name} ({b.run_id})", title_justify="left")
        for col in ("metric", "before", "after", "Δ", "95% CI", "p (Holm)", ""):
            t.add_column(col, justify="left" if col in ("metric", "") else "right")
        for d in c.metrics.values():
            color = {"improved": "green", "regressed": "red"}.get(d.direction, "dim")
            ci = f"{_fmt(d.ci_low)} – {_fmt(d.ci_high)}" if d.ci_low is not None else ""
            t.add_row(
                d.metric,
                _fmt(d.a),
                _fmt(d.b),
                _fmt(d.delta),
                ci,
                _fmt(d.p_adjusted),
                f"[{color}]{d.direction}[/]",
            )
        out.print(t)
        if c.pairwise:
            p = c.pairwise
            out.print(
                f"Head to head ({p['criterion']}): candidate wins {p['win_rate']:.0%} (95% CI {p['ci_low']:.0%}–{p['ci_high']:.0%}), position consistency {p['position_consistency']:.0%}"
            )
        if output:
            out.print(f"[green]wrote[/green] {output}")
    if fail_on_regression and c.regressed:
        raise typer.Exit(1)


@app.command()
def runs(as_json: bool = typer.Option(False, "--json")) -> None:
    """List saved runs (newest first)."""
    from guage_kit.runner.store import RunStore

    items = RunStore().list()
    if as_json:
        out.print_json(json.dumps(items))
        return
    if not items:
        out.print("No saved runs in .guage/runs yet.")
        return
    t = Table()
    for col in ("run_id", "name", "created_at", "samples", "verdict"):
        t.add_column(col)
    for i in items:
        t.add_row(
            str(i["run_id"]),
            str(i["name"]),
            str(i["created_at"]),
            str(i["samples"]),
            str(i["verdict"] or ""),
        )
    out.print(t)


@baseline_app.command("set")
def baseline_set(
    run_ref: str = typer.Argument("latest"), name: str = typer.Option("main", "--name")
) -> None:
    """Copy a run to .guage/baselines/<name>.json (use it as baseline:<name>)."""
    from guage_kit.runner.store import RunStore

    try:
        p = RunStore().set_baseline(run_ref, name)
    except GuageError as exc:
        _fail(exc)
        return
    out.print(f"[green]baseline {name}[/green] → {p}")


@baseline_app.command("show")
def baseline_show(name: str = typer.Option("main", "--name")) -> None:
    """Print a baseline's metrics."""
    from guage_kit.runner.store import RunStore

    try:
        _print_run(RunStore().load(f"baseline:{name}"))
    except GuageError as exc:
        _fail(exc)


@metrics_app.command("list")
def metrics_list(
    family: str = typer.Option(
        None, "--family", "-f", help="Only this family (prefix match, e.g. ananke)."
    ),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """List every metric with its family and required fields."""
    from guage_kit.metrics.registry import list_metrics

    items = [m for m in list_metrics() if family is None or m["family"].startswith(family)]
    if as_json:
        out.print_json(json.dumps(items))
        return
    t = Table(title=f"{len(items)} metrics")
    for col in ("name", "family", "level", "needs", "description"):
        t.add_column(col, overflow="fold")
    for m in items:
        needs = ", ".join(
            m["requires"] + ([" or ".join(m["requires_any"])] if m["requires_any"] else [])
        )
        if m["needs_judge"]:
            needs += " · judge"
        t.add_row(m["name"], m["family"], m["level"], needs, m["description"][:110])
    out.print(t)


@metrics_app.command("show")
def metrics_show(name: str) -> None:
    """Show one metric's declaration and parameters."""
    from guage_kit.metrics.registry import get_metric

    try:
        out.print_json(json.dumps(get_metric(name).describe(), default=str))
    except GuageError as exc:
        _fail(exc)


@data_app.command("validate")
def data_validate(path: Path) -> None:
    """Load a dataset and report problems (exit 2 on the first invalid record)."""
    from guage_kit.core.dataset import Dataset

    try:
        ds = Dataset.load(path)
    except GuageError as exc:
        _fail(exc)
        return
    out.print(f"[green]valid[/green]: {len(ds)} samples · {ds.fingerprint[:23]}")


@data_app.command("stats")
def data_stats(path: Path, as_json: bool = typer.Option(False, "--json")) -> None:
    """Field coverage, tags and lengths, and the metrics `auto` would choose."""
    from guage_kit.core.dataset import Dataset
    from guage_kit.runner.evaluate import auto_metrics

    try:
        ds = Dataset.load(path)
    except GuageError as exc:
        _fail(exc)
        return
    st = ds.stats()
    st["auto_metrics"] = auto_metrics(ds.samples)
    if not st["auto_metrics"] and "output" not in st["fields"]:
        st["note"] = (
            "no outputs yet: run it with a target (--target) and metrics are chosen from what the target returns"
        )
    if as_json:
        out.print_json(json.dumps(st))
        return
    out.print(f"[bold]{st['name']}[/bold]: {st['samples']} samples · {st['fingerprint'][:23]}")
    out.print("Fields: " + ", ".join(f"{k} {v}" for k, v in st["fields"].items()))
    if st["tags"]:
        out.print("Tags: " + ", ".join(f"{k} {v}" for k, v in list(st["tags"].items())[:20]))
    out.print("Auto metrics: " + (", ".join(st["auto_metrics"]) or "none"))
    if st.get("note"):
        out.print(f"[yellow]note:[/yellow] {st['note']}")


@data_app.command("convert")
def data_convert(source: Path, dest: Path) -> None:
    """Convert between .jsonl, .json, .yaml and .csv (field aliases are normalised)."""
    from guage_kit.core.dataset import Dataset

    try:
        Dataset.load(source).save(dest)
    except GuageError as exc:
        _fail(exc)
        return
    out.print(f"[green]wrote[/green] {dest}")


@data_app.command("split")
def data_split(
    source: Path,
    fraction: float = typer.Option(0.5, "--fraction"),
    seed: int = typer.Option(0, "--seed"),
) -> None:
    """Split into <name>.a.jsonl and <name>.b.jsonl (for dev/test or train/holdout)."""
    from guage_kit.core.dataset import Dataset

    try:
        a, b = Dataset.load(source).split(fraction, seed=seed)
    except GuageError as exc:
        _fail(exc)
        return
    for part, ds in (("a", a), ("b", b)):
        p = source.with_name(f"{source.stem}.{part}.jsonl")
        ds.save(p)
        out.print(f"[green]wrote[/green] {p} ({len(ds)})")


@data_app.command("sample")
def data_sample(
    source: Path,
    n: int = typer.Option(..., "-n"),
    dest: Path = typer.Option(..., "-o"),
    seed: int = typer.Option(0, "--seed"),
) -> None:
    """Write a reproducible random sample of n records."""
    from guage_kit.core.dataset import Dataset

    try:
        Dataset.load(source).sample(n, seed=seed).save(dest)
    except GuageError as exc:
        _fail(exc)
        return
    out.print(f"[green]wrote[/green] {dest}")


@judge_app.command("calibrate")
def judge_calibrate(
    data: Path = typer.Argument(
        ..., help="Samples with a human score in metadata (see --human-field)."
    ),
    judge: str = typer.Option("heuristic", "--judge"),
    criterion: str = typer.Option("correctness", "--criterion"),
    human_field: str = typer.Option(
        "human_score", "--human-field", help="metadata key holding the 1–5 human grade."
    ),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Grade labelled samples with a judge and report agreement with the human grades."""
    from guage_kit.core.dataset import Dataset
    from guage_kit.judges import agreement, make_judge

    try:
        ds = Dataset.load(data)
        j = make_judge(judge)
        assert j is not None  # noqa: S101 - make_judge returns a judge for any non-empty spec
        pairs = [
            (j.grade(s, criterion).raw_score, float(s.metadata[human_field]))
            for s in ds
            if human_field in s.metadata
        ]
        if not pairs:
            raise GuageError("GK-DATA-003", f"no sample has metadata.{human_field}")
        res = agreement([float(p[0] or 0) for p in pairs], [p[1] for p in pairs])
    except GuageError as exc:
        _fail(exc)
        return
    if as_json:
        out.print_json(json.dumps(res, default=str))
        return
    out.print(
        f"Judge {j.name} on {criterion}: agreement [bold]{res['verdict']}[/bold] over {res['n']} samples"
    )
    for k in ("quadratic_kappa", "spearman", "exact_agreement", "within_one", "mae", "bias"):
        v = res[k]
        out.print(f"  {k:16} {_fmt(v) if isinstance(v, float) else v}")


@probe_app.command("redteam")
def probe_redteam(
    output: Path = typer.Option(Path("redteam.jsonl"), "-o"),
    system_prompt: Path = typer.Option(
        None, "--system-prompt", help="A file with your system prompt, to test leakage."
    ),
) -> None:
    """Write a red-team dataset (prompt injection, extraction, PII, over-refusal). Run it with --target."""
    from guage_kit.probes import redteam_dataset

    sp = system_prompt.read_text(encoding="utf-8") if system_prompt else None
    redteam_dataset(system_prompt=sp).save(output)
    out.print(
        f"[green]wrote[/green] {output}. Next: guage run --data {output} --target <your target>"
    )


@probe_app.command("perturb")
def probe_perturb(
    source: Path,
    output: Path = typer.Option(..., "-o"),
    kinds: str = typer.Option("typos,lowercase,filler,distractor", "--kinds"),
    seed: int = typer.Option(0, "--seed"),
) -> None:
    """Write perturbed variants of a dataset's inputs (and contexts) for robustness runs."""
    from guage_kit.core.dataset import Dataset
    from guage_kit.probes import PERTURBATIONS, perturb

    names = [k.strip() for k in kinds.split(",") if k.strip()]
    bad = [k for k in names if k not in PERTURBATIONS]
    if bad:
        _fail(
            GuageError(
                "GK-CONFIG-001",
                f"unknown perturbation {', '.join(bad)}",
                hint=", ".join(PERTURBATIONS),
            )
        )
    try:
        perturb(Dataset.load(source), names, seed=seed).save(output)
    except GuageError as exc:
        _fail(exc)
        return
    out.print(f"[green]wrote[/green] {output}")


@probe_app.command("robustness")
def probe_robustness(
    source: Path,
    target: str = typer.Option(..., "--target"),
    kinds: str = typer.Option("typos,lowercase,filler,distractor", "--kinds"),
    metrics: str = typer.Option(None, "--metrics"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Run a target on originals and perturbed inputs; report output agreement and metric drops."""
    from guage_kit.core.dataset import Dataset
    from guage_kit.probes import robustness

    try:
        res = robustness(
            Dataset.load(source),
            target,
            kinds=[k.strip() for k in kinds.split(",")],
            metrics=metrics.split(",") if metrics else None,
        )
    except GuageError as exc:
        _fail(exc)
        return
    res.pop("runs", None)
    if as_json:
        out.print_json(json.dumps(res, default=str))
        return
    out.print(f"Robustness score (output agreement): [bold]{_fmt(res['robustness_score'])}[/bold]")
    for kind, r in res["perturbations"].items():
        worst = sorted(r["metric_delta"].items(), key=lambda kv: kv[1])[:3]
        out.print(
            f"  {kind:18} agreement {_fmt(r['output_agreement'])}  "
            + "  ".join(f"{m} {d:+.3f}" for m, d in worst)
        )


@app.command()
def synth(
    paths: list[Path] = typer.Argument(..., help="Documents or folders (.md, .txt, .rst, .html)."),
    output: Path = typer.Option(Path("synthetic.jsonl"), "-o"),
    provider: str = typer.Option(
        None, "--provider", help="A model for natural questions; omit for offline cloze questions."
    ),
    per_chunk: int = typer.Option(1, "--per-chunk"),
    corpus: Path = typer.Option(
        None, "--corpus", help="Also write the chunks (the corpus to index)."
    ),
) -> None:
    """Generate a test set from your own documents."""
    from guage_kit.synth import chunk, cloze_dataset, generate_qa, read_documents, write_corpus

    chunks = chunk(read_documents(paths))
    if not chunks:
        _fail(GuageError("GK-DATA-004", "no text found in the given documents"))
    try:
        ds = (
            generate_qa(chunks, provider, per_chunk=per_chunk)
            if provider
            else cloze_dataset(chunks, per_chunk=per_chunk)
        )
    except GuageError as exc:
        _fail(exc)
        return
    ds.save(output)
    if corpus:
        write_corpus(chunks, corpus)
    out.print(f"[green]wrote[/green] {output} ({len(ds)} samples from {len(chunks)} chunks)")


@app.command()
def demo(
    output: Path = typer.Option(Path("guage-demo"), "-o", "--output"),
    profile: str = typer.Option("private", "--profile"),
) -> None:
    """Evaluate three demo systems offline and write their reports (no model, no network)."""
    from guage_kit.demo import run_demo

    files = run_demo(output, profile=profile)
    for k, p in files.items():
        if not k.endswith("_run"):
            out.print(f"[green]wrote[/green] {p}")
    out.print(f"Open {files['rag_compare']} in a browser.")


def main() -> None:
    try:
        app()
    except GuageError as exc:  # pragma: no cover - commands handle their own; this is a last resort
        err.print(f"[red]error[/red] {exc}")
        sys.exit(2)


if __name__ == "__main__":  # pragma: no cover
    main()
