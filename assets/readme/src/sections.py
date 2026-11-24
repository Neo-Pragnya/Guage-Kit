"""Generated README sections (scripts/readme_sections.py readme_sections.json): read from the installed package, so the
README's catalogue, command list and error codes cannot fall behind the code."""

from __future__ import annotations

from collections import Counter

DOCS = "https://neo-pragnya.github.io/Guage-Kit/docs/reference"

FAMILIES = [
    ("text", "📝", "Text", "exact and normalised match, token F1, BLEU, chrF, ROUGE, edit distance, numbers, length, readability, diversity"),
    ("semantic", "🧠", "Semantic", "embedding similarity, BERTScore-style token matching"),
    ("rag", "📚", "RAG", "faithfulness, hallucination rate, context precision, recall, relevance and use, answer relevancy and correctness, citations"),
    ("retrieval", "🔎", "Retrieval", "precision@k, recall@k, hit rate, MRR, MAP, nDCG (binary or graded), R-precision"),
    ("classification", "🏷️", "Classification", "accuracy, balanced accuracy, precision, recall, F1, Cohen's kappa, MCC"),
    ("calibration", "🎯", "Calibration", "ECE, MCE, Brier score, selective AUROC"),
    ("embeddings", "🧭", "Embedding models", "STS Spearman and Pearson, alignment, uniformity, anisotropy"),
    ("structured", "🧱", "Structured output", "valid JSON or YAML, JSON Schema, field-level accuracy, Python that parses"),
    ("safety", "🛡️", "Safety", "refusal and over-refusal, personal data, secrets, prompt injection, system-prompt leakage, toxicity, fairness"),
    ("agent", "🤖", "Agents", "tool-call F1, argument accuracy, sequence match, error and redundancy rates, goal success"),
    ("runtime", "⏱️", "Runtime", "latency percentiles, tokens, cost"),
    ("judge", "⚖️", "LLM judge", "a judge's grade on one of 11 criteria or your own rubric"),
]


def families() -> str:
    from guage_kit.metrics.registry import list_metrics

    items = list_metrics()
    counts = Counter(m["family"] for m in items if m["source"] != "ananke-plexus")
    ananke = sum(1 for m in items if m["source"] == "ananke-plexus")
    missing = sorted(set(counts) - {f for f, *_ in FAMILIES})
    if missing:
        raise SystemExit(f"describe these metric families in assets/readme/src/sections.py: {missing}")
    rows = ["| | family | metrics | what it covers |", "| --- | --- | ---: | --- |"]
    for fam, icon, title, text in FAMILIES:
        rows.append(f"| {icon} | [**{title}**]({DOCS}/metrics/{fam}/) | {counts[fam]} | {text} |")
    rows.append(
        f"| 🧬 | [**Ananke Plexus evaluators**]({DOCS}/metrics/ananke/) | {ananke} | agent traces: outcome, trajectory, "
        "tool use, planning, retrieval, safety, resilience, efficiency, multi-agent, architecture |"
    )
    rows.append(f"| | **Total** | **{sum(counts.values()) + ananke}** | |")
    return "\n".join(rows)


def cli() -> str:
    import typer.main

    from guage_kit.cli import app

    root = typer.main.get_command(app)
    rows = ["| command | what it does |", "| --- | --- |"]

    def walk(cmd, path: list[str]) -> None:  # type: ignore[no-untyped-def]
        if hasattr(cmd, "commands"):
            for name in sorted(cmd.commands):
                walk(cmd.commands[name], [*path, name])
            return
        text = " ".join((cmd.help or "").split("\n\n")[0].split()).replace("|", "\\|").replace("<", "&lt;")
        rows.append(f"| `{' '.join(path)}` | {text} |")

    walk(root, ["guage"])
    return "\n".join(rows)


def errors() -> str:
    from guage_kit.errors import CODES

    rows = ["| code | meaning |", "| --- | --- |"]
    rows += [f"| `{code}` | {text} |" for code, text in CODES.items()]
    return "\n".join(rows)
