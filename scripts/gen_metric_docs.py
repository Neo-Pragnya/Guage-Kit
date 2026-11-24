"""Generate the metric reference from the registry and the metric cards.

Writes docs/reference/metrics.md (the catalogue: one line per metric) and docs/reference/metrics/<family>.md (every
metric's full card: what it measures, how it is computed, parameters, how to read it, pitfalls, a worked example
checked by the test suite, and references). Ananke Plexus evaluators go to docs/reference/metrics/ananke.md.

Usage: python scripts/gen_metric_docs.py [--check]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

from guage_kit.metrics.cards import load_cards, load_evaluator_cards
from guage_kit.metrics.registry import list_metrics

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "docs" / "reference" / "metrics.md"
PAGES = ROOT / "docs" / "reference" / "metrics"

FAMILIES: dict[str, tuple[str, str]] = {
    "text": ("Text", "Matching, overlap (BLEU, chrF, ROUGE), edit distance, numbers, length, readability and diversity."),
    "semantic": ("Semantic similarity", "Embedding similarity and BERTScore-style token matching."),
    "rag": ("RAG", "Grounding, hallucination, context quality, answer relevance and correctness, citations."),
    "retrieval": ("Retrieval", "Ranked-retrieval metrics over document ids: precision, recall, hit rate, MRR, MAP, nDCG."),
    "classification": ("Classification", "Labels against gold labels: accuracy, F1, kappa, MCC."),
    "calibration": ("Calibration", "Whether confidence matches accuracy: ECE, MCE, Brier score, selective AUROC."),
    "embeddings": ("Embedding models", "Evaluating embedding models themselves: STS correlation, alignment, uniformity, anisotropy."),
    "structured": ("Structured output", "JSON and YAML validity, JSON Schema conformance, field accuracy, Python syntax."),
    "safety": ("Safety", "Refusals, personal data and secrets, prompt injection, system-prompt leakage, toxicity, fairness."),
    "agent": ("Agents", "Tool calls: choice, arguments, order, errors, redundancy and goal success."),
    "runtime": ("Runtime and cost", "Latency, tokens and cost."),
    "judge": ("LLM judge", "A judge's grade on a criterion or your own rubric."),
}

FIELD_LABEL = {
    "measures": "What it measures",
    "method": "How it is computed",
    "inputs": "Inputs",
    "interpret": "How to read it",
}


def _fmt_range(r: list[Any], hib: bool) -> str:
    lo = "−∞" if r[0] is None else f"{r[0]:g}"
    hi = "∞" if r[1] is None else f"{r[1]:g}"
    return f"{lo} to {hi}, {'higher' if hib else 'lower'} is better"


def _needs(m: dict[str, Any]) -> str:
    parts = [f"`{f}`" for f in m["requires"]]
    if m["requires_any"]:
        parts.append(" or ".join(f"`{f}`" for f in m["requires_any"]))
    if m["needs_judge"]:
        parts.append("a judge")
    if m["needs_embedder"]:
        parts.append("an embedder")
    return ", ".join(parts) or "–"


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def _link(name: str, family_of: dict[str, str], here: str) -> str:
    fam = family_of.get(name)
    if fam is None:
        return f"`{name}`"
    if name.startswith("ananke."):
        target = "ananke.md" if here != "ananke" else ""
    else:
        target = f"{fam}.md" if fam != here else ""
    return f"[`{name}`]({target}#{_anchor(name)})"


def _anchor(name: str) -> str:
    return name.lower().replace(".", "").replace(" ", "-")


def _references(refs: list[dict[str, str]]) -> list[str]:
    out = []
    for r in refs:
        url = r.get("url")
        out.append(f"- {r['citation']}" + (f" <{url}>" if url else ""))
    return out


def _example(name: str, ex: dict[str, Any]) -> list[str]:
    lines = ["**Example** (checked by the test suite against the real metric)", "", "```jsonl"]
    for s in ex["samples"]:
        lines.append(json.dumps(s, ensure_ascii=False))
    lines.append("```")
    if ex.get("params"):
        lines += ["", "```yaml", yaml.safe_dump({"metrics": [{"name": name, "params": ex["params"]}]}, sort_keys=False, allow_unicode=True).rstrip(), "```"]
    lines += ["", f"Result: **{ex['value']:g}**" + (f". {ex['note'].rstrip('.')}." if ex.get("note") else ""), ""]
    return lines


def render_metric(m: dict[str, Any], card: dict[str, Any], family_of: dict[str, str], here: str) -> list[str]:
    name = m["name"]
    lines = [f"## {name}", "", f"*{card['summary'].strip()}*", ""]
    facts = [
        f"**Level:** {m['level']}",
        f"**Range:** {_fmt_range(m['range'], m['higher_is_better'])}",
        f"**Needs:** {_needs(m)}",
        f"**Deterministic:** {'yes' if m['deterministic'] else 'no'}",
    ]
    if m["extra"]:
        facts.append(f"**Extra:** `pip install 'guage-kit[{m['extra']}]'`")
    lines += [" · ".join(facts), ""]
    for key in ("measures", "method"):
        if card.get(key):
            lines += [f"**{FIELD_LABEL[key]}**", "", card[key].strip(), ""]
    if card.get("formula"):
        lines += ["```text", card["formula"].rstrip(), "```", ""]
    if card.get("inputs"):
        lines += [f"**{FIELD_LABEL['inputs']}:** {card['inputs'].strip()}", ""]
    params = m["params"]
    if params:
        lines += ["**Parameters**", "", "| parameter | default | meaning |", "| --- | --- | --- |"]
        for p, default in params.items():
            lines.append(f"| `{p}` | `{default!r}` | {_cell((card.get('params') or {}).get(p, ''))} |")
        lines.append("")
    if card.get("interpret"):
        lines += [f"**{FIELD_LABEL['interpret']}**", "", card["interpret"].strip(), ""]
    if card.get("use_when"):
        lines += ["**Use it when**", "", *[f"- {u}" for u in card["use_when"]], ""]
    if card.get("pitfalls"):
        lines += ["**Pitfalls**", "", *[f"- {p}" for p in card["pitfalls"]], ""]
    if card.get("example"):
        lines += _example(name, card["example"])
    if card.get("related"):
        lines += ["**Related:** " + ", ".join(_link(r, family_of, here) for r in card["related"]), ""]
    if card.get("references"):
        lines += ["**References**", "", *_references(card["references"]), ""]
    return lines


def _frontmatter(title: str, description: str) -> list[str]:
    return ["---", f"title: {title}", f"description: {json.dumps(description)}", "---", ""]


def render_family(fam: str, metrics: list[dict[str, Any]], cards: dict[str, dict[str, Any]], family_of: dict[str, str]) -> str:
    title, blurb = FAMILIES.get(fam, (fam.title(), ""))
    lines = [*_frontmatter(f"{title} metrics", blurb), f"# {title} metrics", "", "> [!NOTE]",
             "> Generated from the metric registry and the metric cards (`guage_kit/metrics/cards/`). Every example",
             "> on this page is run by the test suite, so the numbers are what the metric really returns.", "",
             blurb, "", "| metric | in one line |", "| --- | --- |"]
    for m in metrics:
        lines.append(f"| [`{m['name']}`](#{_anchor(m['name'])}) | {_cell(cards[m['name']]['summary'])} |")
    lines.append("")
    for m in metrics:
        lines += render_metric(m, cards[m["name"]], family_of, fam)
    return "\n".join(lines).rstrip() + "\n"


def render_ananke(metrics: list[dict[str, Any]], family_of: dict[str, str]) -> str:
    cards = load_evaluator_cards()
    lines = [*_frontmatter("Ananke Plexus evaluators", "The 77 agent-trace evaluators from Ananke Plexus, available as ananke.* metrics."),
             "# Ananke Plexus evaluators", "", "> [!NOTE]",
             "> Generated from the installed Ananke Plexus and the evaluator cards (`guage_kit/metrics/cards/ananke/`).", "",
             "Guage Kit discovers every evaluator in the installed `ananke-plexus` and exposes it as a metric named by its",
             "id. Each runs on the sample's agent trace: the recorded `trace` when present, otherwise one built from the",
             "sample's tool calls, contexts, usage and output. Each scores a sample 1 (pass) or 0 (fail) unless stated.",
             "Arguments come from the metric's `params`, then the sample's `metadata.ananke`, then its expected tool names,",
             "then `metadata.<argument>`; see the [agents guide](../../guides/agents.md).", ""]
    by_dim: dict[str, list[dict[str, Any]]] = {}
    for m in metrics:
        by_dim.setdefault(m["family"].removeprefix("ananke."), []).append(m)
    lines += ["| dimension | evaluators |", "| --- | --- |"]
    for dim in sorted(by_dim):
        lines.append(f"| {dim.replace('_', ' ')} | " + ", ".join(f"[`{m['name'].split('.')[-1]}`](#{_anchor(m['name'])})" for m in by_dim[dim]) + " |")
    lines.append("")
    for dim in sorted(by_dim):
        for m in by_dim[dim]:
            name = m["name"]
            card = cards.get(name, {})
            lines += [f"## {name}", "", f"*{(card.get('summary') or m['description']).strip()}*", "",
                      f"**Dimension:** {dim.replace('_', ' ')} · **Deterministic:** {'yes' if m['deterministic'] else 'no'}", ""]
            if card.get("method"):
                lines += ["**How it is computed**", "", card["method"].strip(), ""]
            if m["params"]:
                lines += ["**Arguments**", "", "| argument | default | meaning |", "| --- | --- | --- |"]
                for p, default in m["params"].items():
                    d = "required" if p in m["required_params"] else f"`{default!r}`"
                    lines.append(f"| `{p}` | {d} | {_cell((card.get('arguments') or {}).get(p, ''))} |")
                lines.append("")
            if card.get("passes_when"):
                lines += [f"**Passes when:** {card['passes_when'].strip()}", ""]
            if card.get("use_when"):
                lines += ["**Use it when**", "", *[f"- {u}" for u in card["use_when"]], ""]
            if card.get("pitfalls"):
                lines += ["**Pitfalls**", "", *[f"- {p}" for p in card["pitfalls"]], ""]
            if card.get("example"):
                lines += ["**Example**", "", "```yaml", card["example"].rstrip(), "```", ""]
            if card.get("references"):
                lines += ["**References**", "", *_references(card["references"]), ""]
    return "\n".join(lines).rstrip() + "\n"


def render_catalogue(native: list[dict[str, Any]], ananke: list[dict[str, Any]], cards: dict[str, dict[str, Any]]) -> str:
    lines = [*_frontmatter("Metric reference", "Every metric Guage Kit ships: what it measures, how it is computed, how to read it, and the papers behind it."),
             "# Metric reference", "", "> [!NOTE]",
             "> Generated by `scripts/gen_metric_docs.py` from the metric registry and the metric cards. `guage metrics list`",
             "> and `guage metrics show <name>` print the same information for the installed version.", "",
             f"Guage Kit has **{len(native)} native metrics** and exposes **{len(ananke)} Ananke Plexus evaluators**, "
             f"{len(native) + len(ananke)} in total. Each family page documents every metric in full: what it measures, how it",
             "is computed (with the formula), its parameters, how to read the number, when to use it, its pitfalls, a worked",
             "example that the test suite runs, and the papers that define it.", "",
             "↑ means higher is better and ↓ lower is better. *Sample* metrics score each sample and report the mean with a",
             "bootstrap interval; *corpus* metrics are computed over the whole set, and their interval comes from resampling",
             "the samples. Retrieval metrics take a cut-off: `recall@5`, `ndcg@10`.", ""]
    by_fam: dict[str, list[dict[str, Any]]] = {}
    for m in native:
        by_fam.setdefault(m["family"], []).append(m)
    order = [f for f in FAMILIES if f in by_fam] + sorted(f for f in by_fam if f not in FAMILIES)
    lines += ["| family | metrics | covers |", "| --- | ---: | --- |"]
    for fam in order:
        title, blurb = FAMILIES.get(fam, (fam.title(), ""))
        lines.append(f"| [{title}](metrics/{fam}.md) | {len(by_fam[fam])} | {blurb} |")
    lines.append(f"| [Ananke Plexus evaluators](metrics/ananke.md) | {len(ananke)} | Agent traces: outcome, trajectory, tool use, planning, retrieval, safety, resilience, efficiency, multi-agent, architecture. |")
    lines.append("")
    for fam in order:
        title, _ = FAMILIES.get(fam, (fam.title(), ""))
        lines += [f"## {title}", "", "| metric | level | needs | in one line |", "| --- | --- | --- | --- |"]
        for m in by_fam[fam]:
            arrow = "↑" if m["higher_is_better"] else "↓"
            lines.append(f"| [`{m['name']}`](metrics/{fam}.md#{_anchor(m['name'])}) {arrow} | {m['level']} | {_needs(m)} | {_cell(cards[m['name']]['summary'])} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_all() -> dict[Path, str]:
    items = list_metrics()
    native = [m for m in items if m["source"] != "ananke-plexus"]
    ananke = [m for m in items if m["source"] == "ananke-plexus"]
    cards = load_cards()
    missing = [m["name"] for m in native if m["name"] not in cards]
    if missing:
        raise SystemExit(f"metrics without a card: {missing}")
    family_of = {m["name"]: m["family"] for m in native} | {m["name"]: "ananke" for m in ananke}
    by_fam: dict[str, list[dict[str, Any]]] = {}
    for m in native:
        by_fam.setdefault(m["family"], []).append(m)
    files = {CATALOGUE: render_catalogue(native, ananke, cards)}
    for fam, ms in by_fam.items():
        files[PAGES / f"{fam}.md"] = render_family(fam, ms, cards, family_of)
    files[PAGES / "ananke.md"] = render_ananke(ananke, family_of)
    return files


if __name__ == "__main__":
    files = render_all()
    if "--check" in sys.argv:
        stale = [p for p, t in files.items() if not p.exists() or p.read_text(encoding="utf-8") != t]
        stale += [p for p in PAGES.glob("*.md") if p not in files]
        if stale:
            print(f"metric reference is out of date ({', '.join(p.name for p in stale)}): run python scripts/gen_metric_docs.py")
            sys.exit(1)
        print("metrics.md is up to date")
    else:
        PAGES.mkdir(parents=True, exist_ok=True)
        for p in PAGES.glob("*.md"):
            if p not in files:
                p.unlink()
        for p, t in files.items():
            p.write_text(t, encoding="utf-8")
        print(f"wrote {len(files)} pages")
