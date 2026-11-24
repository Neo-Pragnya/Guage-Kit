"""Reports: one offline HTML file per run or comparison, plus Markdown (PR comments, CI summaries), JUnit XML
(CI test views) and JSON."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape, quoteattr

from guage_kit.core.results import RunResult
from guage_kit.reports.html import render_html, view_model, write_report


def _fmt(v: float | None, digits: int = 3) -> str:
    if v is None:
        return "–"
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:.{digits}f}"


_ICON = {"PASS": "✅", "WARN": "⚠️", "REVIEW": "🔎", "BLOCK": "⛔"}


def markdown(run: RunResult, comparison: Any = None, *, max_rows: int = 40) -> str:
    """A compact Markdown summary for a pull request comment or ``$GITHUB_STEP_SUMMARY``."""
    lines = [f"## Guage Kit · {run.name}", ""]
    if run.gate:
        lines.append(f"**Gate: {_ICON.get(run.gate.verdict, '')} {run.gate.verdict}**")
        lines.append("")
    lines.append(
        f"{run.dataset.get('samples', len(run.samples))} samples · dataset `{str(run.dataset.get('fingerprint', ''))[:19]}` · run `{run.run_id}`"
    )
    lines += [
        "",
        "| metric | value | 95% CI | n | threshold |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    for s in list(run.summaries.values())[:max_rows]:
        ci = f"[{_fmt(s.ci_low)}, {_fmt(s.ci_high)}]" if s.ci_low is not None else ""
        arrow = "↑" if s.higher_is_better else "↓"
        lines.append(
            f"| {s.metric} {arrow} | {_fmt(s.value)} | {ci} | {s.n} | {_fmt(s.threshold) if s.threshold is not None else ''} |"
        )
    if run.gate and run.gate.checks:
        lines += ["", "### Gate checks", ""]
        for c in run.gate.checks:
            lines.append(f"- {'✅' if c.ok else '❌'} **{c.metric}**: {c.message}")
    if comparison is not None:
        lines += [
            "",
            f"### Versus {comparison.run_a.get('name', '')} (`{comparison.run_a.get('run_id', '')}`)",
            "",
            "| metric | before | after | Δ | p (Holm) | |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
        for d in comparison.metrics.values():
            mark = {
                "improved": "🟢 improved",
                "regressed": "🔴 regressed",
                "unchanged": "⚪ unchanged",
                "changed": "~ changed (untested)",
            }.get(d.direction, "· inconclusive")
            lines.append(
                f"| {d.metric} | {_fmt(d.a)} | {_fmt(d.b)} | {_fmt(d.delta)} | {_fmt(d.p_adjusted)} | {mark} |"
            )
    if run.notes:
        lines += ["", *[f"> {n}" for n in run.notes]]
    return "\n".join(lines) + "\n"


def junit(run: RunResult) -> str:
    """JUnit XML: one test case per gate check (or per thresholded metric), so CI shows quality as tests."""
    cases: list[str] = []
    failures = 0
    if run.gate and run.gate.checks:
        for c in run.gate.checks:
            name = quoteattr(f"gate.{c.metric}")
            if c.ok:
                cases.append(f'<testcase classname="guage.gate" name={name}/>')
            else:
                failures += 1
                kind = "failure" if c.rule.on_fail == "block" else "skipped"
                cases.append(
                    f'<testcase classname="guage.gate" name={name}><{kind} message={quoteattr(c.message)}/></testcase>'
                )
    for s in run.summaries.values():
        name = quoteattr(f"metric.{s.metric}")
        value = escape(_fmt(s.value, 4))
        if s.threshold is not None and s.value is not None:
            ok = s.value >= s.threshold if s.higher_is_better else s.value <= s.threshold
            if not ok:
                failures += 1
                cases.append(
                    f'<testcase classname="guage.metric" name={name}><failure message={quoteattr(f"{s.metric}={value} misses threshold {s.threshold}")}/></testcase>'
                )
                continue
        cases.append(
            f'<testcase classname="guage.metric" name={name}><system-out>{value}</system-out></testcase>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<testsuite name={quoteattr("guage-kit:" + run.name)} tests="{len(cases)}" failures="{failures}" time="{run.duration_s}">\n  '
        + "\n  ".join(cases)
        + "\n</testsuite>\n"
    )


def write_all(
    run: RunResult, out_dir: str | Path, *, comparison: Any = None, profile: str = "private"
) -> dict[str, Path]:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    return {
        "html": write_report(run, d / "report.html", comparison=comparison, profile=profile),
        "markdown": _write(d / "summary.md", markdown(run, comparison)),
        "junit": _write(d / "junit.xml", junit(run)),
        "json": run.save(d / "run.json"),
    }


def _write(p: Path, text: str) -> Path:
    p.write_text(text, encoding="utf-8")
    return p


__all__ = ["junit", "markdown", "render_html", "view_model", "write_all", "write_report"]
