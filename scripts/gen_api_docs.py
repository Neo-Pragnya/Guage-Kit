"""Generate the Python API and CLI reference (docs/reference/api/*.md) from the code.

Signatures, model fields and docstrings come from the installed package, so the reference cannot drift from the
code (tests/test_docs.py fails when it is out of date).

Usage: python scripts/gen_api_docs.py [--check]
"""

from __future__ import annotations

import importlib
import json
import inspect
import re
import sys
from pathlib import Path
from typing import Any

import typer.main
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "reference" / "api"
REPO = "https://github.com/Neo-Pragnya/Guage-Kit/blob/main/"

# page id → (title, description, intro, [(module, names or None for __all__)])
PAGES: dict[str, tuple[str, str, str, list[tuple[str, list[str] | None]]]] = {
    "evaluation": (
        "Evaluation and comparison",
        "evaluate(), compare(), run storage and targets: the functions that produce and compare runs.",
        "The top-level package re-exports the everyday names (`from guage_kit import evaluate, compare, Dataset`). "
        "This page documents them where they are defined.",
        [
            ("guage_kit.runner.evaluate", None),
            ("guage_kit.runner.compare", None),
            ("guage_kit.runner.store", None),
            ("guage_kit.runner.target", None),
        ],
    ),
    "data": (
        "Samples, datasets and results",
        "The data model: Sample, Dataset, and the run records (RunResult, Score, MetricSummary, gates).",
        "Every metric reads a `Sample`; every run produces a `RunResult` that is saved as `run.json` and rendered into "
        "reports.",
        [
            ("guage_kit.core.sample", None),
            ("guage_kit.core.dataset", None),
            ("guage_kit.core.results", None),
        ],
    ),
    "metrics": (
        "Metric registry and plugins",
        "Declaring metrics, resolving metric specs, the registry, metric cards and embedders.",
        "Use `@metric` and `@corpus_metric` to add your own metrics; register them for other projects through the "
        "`guage_kit.metrics` entry-point group. Each built-in metric is described in the "
        "[metric reference](../metrics.md).",
        [
            ("guage_kit.metrics.registry", None),
            ("guage_kit.metrics.cards", None),
            ("guage_kit.metrics.semantic", ["Embedder", "HashingEmbedder", "SentenceTransformerEmbedder", "make_embedder"]),
        ],
    ),
    "judges": (
        "Judges and providers",
        "LLM and heuristic judges, criteria, calibration against human labels, and model providers.",
        "A judge grades samples on a [criterion](criteria.md). `make_judge('heuristic')` works offline; "
        "`make_judge('anthropic:claude-opus-5-5')` and the other provider specs use a model.",
        [
            ("guage_kit.judges.judge", None),
            ("guage_kit.judges.criteria", None),
            ("guage_kit.judges.calibration", None),
            ("guage_kit.judges.providers", None),
        ],
    ),
    "statistics": (
        "Statistics",
        "Bootstrap intervals, paired tests, multiple-comparison correction, effect sizes and sample-size planning.",
        "See [statistical methods](statistical-methods.md) for what each method assumes and the papers behind it, and "
        "the [statistics guide](../../guides/statistics.md) for how runs use them.",
        [("guage_kit.stats", None)],
    ),
    "probes-and-synthesis": (
        "Probes and synthetic data",
        "Perturbations, robustness runs, red-team datasets and test sets generated from your documents.",
        "The perturbation kinds are listed in [perturbations](perturbations.md).",
        [("guage_kit.probes", None), ("guage_kit.synth", None)],
    ),
    "reports": (
        "Reports",
        "The offline HTML report, Markdown summaries, JUnit XML and the report view model.",
        "Reports are single self-contained files; see the [report format](../report-format.md) for the manifest and "
        "the view model's schema.",
        [("guage_kit.reports", None), ("guage_kit.reports.html", None)],
    ),
    "configuration": (
        "Suites and configuration",
        "guage.yaml suites as Python objects: loading, running and writing configured reports.",
        "The YAML keys are documented in the [configuration reference](../configuration.md).",
        [("guage_kit.config", None)],
    ),
    "ananke-harness": (
        "Ananke Plexus harness",
        "Version negotiation, evaluator discovery and conversion between Guage Kit and Ananke Plexus models.",
        "How the two packages divide the work is explained in [Ananke integration](../../concepts/ananke-integration.md).",
        [
            ("guage_kit.harness.negotiation", None),
            ("guage_kit.harness.catalogue", None),
            ("guage_kit.harness.convert", None),
        ],
    ),
    "errors": (
        "Errors",
        "GuageError and the GK-* error codes.",
        "Every expected failure raises `GuageError` with a stable code and a hint; the CLI prints them and exits 2. "
        "The codes are listed in the [error reference](../errors.md).",
        [("guage_kit.errors", None)],
    ),
}

STAT_METHODS: list[tuple[str, str, str, list[tuple[str, str]]]] = [
    (
        "bootstrap_ci",
        "Percentile bootstrap confidence interval",
        "Resamples the per-sample scores with replacement (2,000 times by default, fixed seed), recomputes the "
        "statistic each time and reports the 2.5th and 97.5th percentiles. Makes no normality assumption; needs the "
        "samples to be representative and independent. Corpus metrics are recomputed on each resample.",
        [
            ("Efron, B. (1979). Bootstrap Methods: Another Look at the Jackknife. The Annals of Statistics, 7(1), 1–26.", "https://doi.org/10.1214/aos/1176344552"),
            ("Efron, B. and Tibshirani, R. J. (1993). An Introduction to the Bootstrap. Chapman & Hall/CRC.", "https://doi.org/10.1201/9780429246593"),
        ],
    ),
    (
        "paired_bootstrap",
        "Paired bootstrap of a difference",
        "Resamples sample ids (not scores) so both systems are compared on the same resampled items, giving an "
        "interval for mean(b − a) and the share of resamples in which b beats a.",
        [
            ("Koehn, P. (2004). Statistical Significance Tests for Machine Translation Evaluation. Proceedings of EMNLP 2004, pp. 388–395.", "https://aclanthology.org/W04-3250/"),
            ("Berg-Kirkpatrick, T., Burkett, D. and Klein, D. (2012). An Empirical Investigation of Statistical Significance in NLP. Proceedings of EMNLP-CoNLL 2012, pp. 995–1005.", "https://aclanthology.org/D12-1091/"),
        ],
    ),
    (
        "permutation_test",
        "Paired permutation (sign-flip) test",
        "Under the null hypothesis the sign of each paired difference is arbitrary; the p-value is the share of sign "
        "assignments whose mean difference is at least as extreme as the observed one. Enumerates all 2^n assignments "
        "when that is at most `n_resamples` (exact), otherwise samples them. This is the test `guage compare` reports.",
        [
            ("Fisher, R. A. (1935). The Design of Experiments. Oliver and Boyd.", ""),
            ("Dror, R., Baumer, G., Shlomov, S. and Reichart, R. (2018). The Hitchhiker's Guide to Testing Statistical Significance in Natural Language Processing. Proceedings of ACL 2018, pp. 1383–1392.", "https://aclanthology.org/P18-1128/"),
        ],
    ),
    (
        "sign_test",
        "Sign test",
        "Counts wins and losses of b over a (ties dropped) and computes an exact two-sided binomial p-value. Uses only "
        "the direction of each difference, so it is robust to outliers but has less power.",
        [("Dixon, W. J. and Mood, A. M. (1946). The Statistical Sign Test. Journal of the American Statistical Association, 41(236), 557–566.", "https://doi.org/10.1080/01621459.1946.10501898")],
    ),
    (
        "wilcoxon",
        "Wilcoxon signed-rank test",
        "Ranks the absolute paired differences and compares the rank sums of positive and negative differences, with "
        "the normal approximation, tie correction and continuity correction. More powerful than the sign test when "
        "differences are roughly symmetric.",
        [("Wilcoxon, F. (1945). Individual Comparisons by Ranking Methods. Biometrics Bulletin, 1(6), 80–83.", "https://doi.org/10.2307/3001968")],
    ),
    (
        "holm",
        "Holm–Bonferroni correction",
        "When many metrics are compared at once, some will look significant by chance. Holm's step-down procedure "
        "sorts the p-values, multiplies the i-th smallest by (m − i + 1), enforces monotonicity and controls the "
        "family-wise error rate at `alpha` without assuming independence.",
        [("Holm, S. (1979). A Simple Sequentially Rejective Multiple Test Procedure. Scandinavian Journal of Statistics, 6(2), 65–70.", "https://www.jstor.org/stable/4615733")],
    ),
    (
        "cohens_d",
        "Cohen's d (paired)",
        "Mean of the paired differences divided by their standard deviation: how large a change is relative to its "
        "noise, independent of sample size. Roughly 0.2 is small, 0.5 medium and 0.8 large.",
        [("Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences (2nd ed.). Lawrence Erlbaum Associates.", "https://doi.org/10.4324/9780203771587")],
    ),
    (
        "min_detectable_effect",
        "Minimum detectable effect and sample size",
        "From the standard deviation of paired differences, the smallest true mean difference a paired test of n "
        "samples detects with the given power (normal approximation), and the inverse: how many samples a given "
        "effect needs. Use it before building a dataset.",
        [("Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences (2nd ed.). Lawrence Erlbaum Associates.", "https://doi.org/10.4324/9780203771587")],
    ),
    (
        "quantile",
        "Quantiles and percentiles",
        "Linear interpolation between order statistics (Hyndman and Fan type 7), used for latency percentiles.",
        [("Hyndman, R. J. and Fan, Y. (1996). Sample Quantiles in Statistical Packages. The American Statistician, 50(4), 361–365.", "https://doi.org/10.1080/00031305.1996.10473566")],
    ),
]


def _front(title: str, description: str) -> list[str]:
    return ["---", f"title: {json.dumps(title)}", f"description: {json.dumps(description)}", "---"]


# ── rendering helpers ─────────────────────────────────────────────────────────────────────────────────────────────
def md_doc(text: str) -> str:
    """Docstrings use reStructuredText roles; render them as Markdown."""
    text = re.sub(r":(?:class|func|meth|attr|mod|data):`~?([^`]+)`", r"`\1`", text)
    text = re.sub(r"``([^`]+)``", r"`\1`", text)
    text = re.sub(r"(?m)^(\s*)Example::\s*$", r"\1**Example**\n", text)
    # indented literal blocks after "**Example**" become fenced code
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        if line.strip() == "**Example**":
            block = []
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith("    ")):
                block.append(lines[i][4:] if lines[i].startswith("    ") else "")
                i += 1
            while block and not block[-1].strip():
                block.pop()
            while block and not block[0].strip():
                block.pop(0)
            out += ["", "```python", *block, "```", ""]
            continue
        i += 1
    return "\n".join(out).strip()


def _default(v: Any) -> str:
    if callable(v):
        return getattr(v, "__name__", type(v).__name__)
    r = repr(v)
    return re.sub(r" at 0x[0-9a-f]+", "", r)


def signature(obj: Any, name: str) -> str:
    try:
        sig = inspect.signature(obj)
    except (TypeError, ValueError):
        return f"{name}(...)"
    params = []
    for p in sig.parameters.values():
        if p.name == "self":
            continue
        s = p.name if p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD) else ("*" if p.kind == p.VAR_POSITIONAL else "**") + p.name
        if p.annotation is not inspect.Parameter.empty:
            s += f": {_ann(p.annotation)}"
        if p.default is not inspect.Parameter.empty:
            s += f" = {_default(p.default)}"
        params.append((p.kind, s))
    parts, star_done = [], False
    for kind, s in params:
        if kind == inspect.Parameter.KEYWORD_ONLY and not star_done:
            parts.append("*")
            star_done = True
        if kind == inspect.Parameter.VAR_POSITIONAL:
            star_done = True
        parts.append(s)
    ret = ""
    if sig.return_annotation is not inspect.Signature.empty:
        ret = f" -> {_ann(sig.return_annotation)}"
    one = f"{name}({', '.join(parts)}){ret}"
    if len(one) <= 100:
        return one
    return f"{name}(\n" + "".join(f"    {p},\n" for p in parts) + f"){ret}"


def _ann(a: Any) -> str:
    s = a if isinstance(a, str) else getattr(a, "__name__", None) or repr(a)
    s = str(s).replace("typing.", "").replace("collections.abc.", "")
    return re.sub(r"\b(?:guage_kit|ananke)\.[\w.]+\.(\w+)", r"\1", s)


def source_link(obj: Any) -> str:
    try:
        path = Path(inspect.getsourcefile(obj) or "").resolve()
        line = inspect.getsourcelines(obj)[1]
        rel = path.relative_to(ROOT)
    except (TypeError, OSError, ValueError):
        return ""
    return f"[source]({REPO}{rel.as_posix()}#L{line})"


def model_fields(cls: type[BaseModel]) -> list[str]:
    rows = ["| field | type | default |", "| --- | --- | --- |"]
    for fname, f in cls.model_fields.items():
        key = f.alias or fname
        if f.is_required():
            default = "required"
        elif f.default_factory is not None:
            default = f"`{_default(f.default_factory())}`"
        else:
            default = f"`{_default(f.default)}`"
        typ = _ann(f.annotation).replace("|", "\\|")
        rows.append(f"| `{key}` | `{typ}` | {default} |")
    return rows


def render_object(name: str, obj: Any, level: str = "###") -> list[str]:
    kind = "class" if inspect.isclass(obj) else "function" if callable(obj) else "constant"
    lines = [f"{level} `{name}`", ""]
    link = source_link(obj) if kind != "constant" else ""
    if kind == "constant":
        val = _default(obj)
        if isinstance(obj, dict) and obj and all(callable(v) for v in obj.values()):
            val = "{" + ", ".join(f"{k!r}: ..." for k in obj) + "}"
        lines += ["```python", f"{name} = {val if len(val) < 300 else val[:300] + ' …'}", "```", ""]
        return lines
    if kind == "class" and issubclass(obj, BaseModel):
        lines += [f"*Pydantic model* {link}".strip(), ""]
    else:
        target = obj.__init__ if kind == "class" and "__init__" in vars(obj) else obj
        sig = signature(target, name)
        lines += ["```python", ("class " if kind == "class" else "") + sig, "```", ""]
        if link:
            lines += [link, ""]
    doc = inspect.getdoc(obj)
    if doc and not (kind == "class" and doc == inspect.getdoc(BaseModel)):
        lines += [md_doc(doc), ""]
    if kind == "class" and issubclass(obj, BaseModel):
        lines += model_fields(obj) + [""]
    if kind == "class":
        for mname, m in vars(obj).items():
            if mname.startswith("_") or not (inspect.isfunction(m) or isinstance(m, (property, classmethod, staticmethod))):
                continue
            fn = m.fget if isinstance(m, property) else getattr(m, "__func__", m)
            mdoc = inspect.getdoc(fn)
            if not mdoc and not inspect.isfunction(m):
                continue
            label = f"{name}.{mname}"
            if isinstance(m, property):
                lines += [f"- **`{label}`** *(property)*" + (f": {md_doc(mdoc)}" if mdoc else "")]
            else:
                lines += [f"- **`{signature(fn, label)}`**" + (f"  \n  {md_doc(mdoc)}" if mdoc else "")]
        lines.append("")
    return lines


def render_page(page_id: str) -> str:
    title, description, intro, modules = PAGES[page_id]
    lines = [*_front(title, description), "", f"# {title}", "", "> [!NOTE]",
             "> Generated from the code by `scripts/gen_api_docs.py`; signatures and docstrings are the installed",
             "> package's.", "", intro, ""]
    for mod_name, names in modules:
        mod = importlib.import_module(mod_name)
        lines += [f"## `{mod_name}`", ""]
        if mod.__doc__ and names is None:
            lines += [md_doc(inspect.cleandoc(mod.__doc__)), ""]
        for n in names or list(getattr(mod, "__all__", [])):
            lines += render_object(n, getattr(mod, n))
    return "\n".join(lines).rstrip() + "\n"


def render_criteria() -> str:
    from guage_kit.judges.criteria import CRITERIA

    lines = [*_front("Judge criteria", "The built-in criteria an LLM or heuristic judge grades on, with every score anchor."), "",
             "# Judge criteria", "", "> [!NOTE]", "> Generated from `guage_kit/judges/criteria.py`.", "",
             "A criterion is a question plus an anchor for every score, so a judge (and a person checking it) knows what a 3",
             "means. Anchored scales make grades more consistent across samples and between judges. Scores are on a 1–5 scale",
             "and reported normalised to 0–1 (`(raw − 1) / 4`). Use one with `metrics: [{name: judge, params: {criterion:",
             "groundedness}}]`, or define your own `{name, question, levels}`.", "",
             "| criterion | sees the reference | sees the contexts |", "| --- | --- | --- |"]
    for name, c in CRITERIA.items():
        lines.append(f"| [`{name}`](#{name}) | {'yes' if c.uses_reference else '–'} | {'yes' if c.uses_contexts else '–'} |")
    lines.append("")
    for name, c in CRITERIA.items():
        lines += [f"## {name}", "", f"**Question.** {c.question}", "", "| score | anchor |", "| ---: | --- |"]
        for score in sorted(c.levels, reverse=True):
            lines.append(f"| {score} | {c.levels[score]} |")
        lines.append("")
    lines += ["## Background", "",
              "- Zheng, L. et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. NeurIPS 2023 Datasets and Benchmarks. [arXiv:2306.05685](https://arxiv.org/abs/2306.05685)",
              "- Liu, Y. et al. (2023). G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment. EMNLP 2023. [ACL Anthology](https://aclanthology.org/2023.emnlp-main.153/)",
              "- Kim, S. et al. (2024). Prometheus: Inducing Fine-grained Evaluation Capability in Language Models. ICLR 2024. [arXiv:2310.08491](https://arxiv.org/abs/2310.08491)",
              "- Wang, P. et al. (2024). Large Language Models are not Fair Evaluators. ACL 2024 (position bias; why pairwise comparisons run in both orders). [ACL Anthology](https://aclanthology.org/2024.acl-long.511/)",
              ""]
    return "\n".join(lines)


def render_perturbations() -> str:
    from guage_kit.probes import PERTURBATION_DESCRIPTIONS, PERTURBATIONS

    lines = [*_front("Perturbations", "Every input and context perturbation used by robustness runs."), "",
             "# Perturbations", "", "> [!NOTE]", "> Generated from `guage_kit/probes`.", "",
             "A robustness run (`guage probe robustness`) evaluates a target on the original samples and on perturbed copies,",
             "then reports how often the output stays the same and how much each metric drops. Perturbations are seeded,",
             "so a run is reproducible. See the [robustness guide](../../guides/robustness.md).", "",
             "| kind | what it changes |", "| --- | --- |"]
    for name in PERTURBATIONS:
        lines.append(f"| `{name}` | {md_doc(PERTURBATION_DESCRIPTIONS[name])} |")
    lines += ["", "## Background", "",
              "- Ribeiro, M. T., Wu, T., Guestrin, C. and Singh, S. (2020). Beyond Accuracy: Behavioral Testing of NLP Models with CheckList. ACL 2020. [ACL Anthology](https://aclanthology.org/2020.acl-main.442/)",
              "- Shi, F. et al. (2023). Large Language Models Can Be Easily Distracted by Irrelevant Context. ICML 2023. [arXiv:2302.00093](https://arxiv.org/abs/2302.00093)",
              "- Liu, N. F. et al. (2024). Lost in the Middle: How Language Models Use Long Contexts. TACL 12. [ACL Anthology](https://aclanthology.org/2024.tacl-1.9/)",
              ""]
    return "\n".join(lines)


def render_stat_methods() -> str:
    lines = [*_front("Statistical methods", "What each statistical method computes, what it assumes, and the papers behind it."), "",
             "# Statistical methods", "",
             "Every number in a Guage Kit run comes with an interval, and every comparison with a test that accounts for",
             "testing many metrics at once. All methods are implemented in plain Python with a fixed seed, so a report can be",
             "regenerated exactly. Function signatures are in the [statistics API](statistics.md).", ""]
    for fn, title, text, refs in STAT_METHODS:
        lines += [f"## {title}", "", f"`guage_kit.stats.{fn}`", "", text, "", "**References**", ""]
        for cite, url in refs:
            lines.append(f"- {cite}" + (f" [{url.split('//')[1].split('/')[0]}]({url})" if url else ""))
        lines.append("")
    return "\n".join(lines)


def render_cli() -> str:
    from guage_kit.cli import app

    root = typer.main.get_command(app)
    lines = [*_front("CLI options", "Every guage command with every argument and option (generated from the CLI)."), "",
             "# CLI options", "", "> [!NOTE]", "> Generated from the CLI by `scripts/gen_api_docs.py`. The [CLI guide](../cli.md) explains the",
             "> commands with examples. Exit codes: 0 success, 1 a gate or regression failed, 2 a usage or `GK-*` error.", ""]

    def walk(cmd: Any, path: list[str]) -> None:
        if hasattr(cmd, "commands"):
            for name in sorted(cmd.commands):
                walk(cmd.commands[name], [*path, name])
            return
        full = " ".join(path)
        lines.extend([f"## `{full}`", "", (cmd.help or "").strip().split("\n\n")[0], ""])
        rows = []
        for p in cmd.params:
            if p.name == "help":
                continue
            helptext = (p.help or "").replace("|", "\\|") or "–"
            d = p.default
            shown = d is not None and d is not ... and not (getattr(p, "is_flag", False) and d is False)
            shown = shown and not _default(d).startswith("<") and d != []
            default = f"`{_default(d)}`" if shown else "–"
            if p.param_type_name == "argument":
                req = "required" if p.required else "optional"
                rows.append(f"| `{(p.name or '').upper()}` | argument, {req} | {default} | {helptext} |")
            else:
                names = ", ".join(f"`{o}`" for o in [*p.opts, *p.secondary_opts])
                kind = "flag" if p.is_flag else "option"
                rows.append(f"| {names} | {kind}{', repeatable' if p.multiple else ''} | {default} | {helptext} |")
        if rows:
            lines.extend(["| name | kind | default | description |", "| --- | --- | --- | --- |", *rows, ""])

    walk(root, ["guage"])
    return "\n".join(lines)


def render_index() -> str:
    lines = [*_front("API reference", "The complete Python API and CLI of Guage Kit, generated from the code."), "",
             "# API reference", "",
             "Everything a program can import from Guage Kit, and every option of the `guage` command, generated from the",
             "installed package. For a guided tour start with the [Python API guide](python-api.md); for the metrics",
             "themselves see the [metric reference](metrics.md).", "",
             "| page | covers |", "| --- | --- |"]
    for pid, (title, desc, _, _) in PAGES.items():
        lines.append(f"| [{title}](api/{pid}.md) | {desc} |")
    lines += ["| [Judge criteria](api/criteria.md) | Every built-in criterion with its score anchors. |",
              "| [Perturbations](api/perturbations.md) | Every robustness perturbation. |",
              "| [Statistical methods](api/statistical-methods.md) | Assumptions and papers behind every statistical method. |",
              "| [CLI options](api/cli-options.md) | Every `guage` command, argument and option. |", ""]
    return "\n".join(lines)


def render_all() -> dict[Path, str]:
    files = {OUT / f"{pid}.md": render_page(pid) for pid in PAGES}
    files[ROOT / "docs" / "reference" / "api.md"] = render_index()
    files[OUT / "criteria.md"] = render_criteria()
    files[OUT / "perturbations.md"] = render_perturbations()
    files[OUT / "statistical-methods.md"] = render_stat_methods()
    files[OUT / "cli-options.md"] = render_cli()
    return files


if __name__ == "__main__":
    files = render_all()
    if "--check" in sys.argv:
        stale = [p.name for p, t in files.items() if not p.exists() or p.read_text(encoding="utf-8") != t]
        stale += [p.name for p in OUT.glob("*.md") if p not in files]
        if stale:
            print(f"docs/reference/api is out of date ({', '.join(sorted(stale))}): run python scripts/gen_api_docs.py")
            sys.exit(1)
        print("API reference is up to date")
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        for p in OUT.glob("*.md"):
            if p not in files:
                p.unlink()
        for p, t in files.items():
            p.write_text(t, encoding="utf-8")
        print(f"wrote {len(files)} pages to {OUT.relative_to(ROOT)}")
