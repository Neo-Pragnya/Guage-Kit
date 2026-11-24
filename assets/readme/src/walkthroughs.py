"""Animated terminal walkthroughs for the README (rendered by the living-diagrams skill's term_flow.py).

Every output line below was captured from real runs of guage-kit 0.1.1 on 2026-11-24 (`guage init`, `guage run`,
`guage demo`, `guage compare`). Tables are trimmed to their most telling rows (and the compare table drops its 95% CI column to fit); no value is
changed. Regenerate when
the commands or their output change:

    python <Skills>/living-diagrams/scripts/term_flow.py assets/readme/src/walkthroughs.py --out assets/readme
"""

THEME = {
    "bg": "#0f1a1f", "panel": "#0b1418", "bar": "#16252b", "ink": "#e6eeeb", "muted": "#8fa1a7",
    "accent": "#f59e0b", "accent2": "#5eead4", "ok": "#5eead4", "warn": "#fbbf24", "err": "#f87171",
    "card": "#12232a", "card_on": "#123b38", "line": "#22383c", "title": "#ffffff",
}

SPECS = [
    {
        "id": "walkthrough-quickstart",
        "title": "⚡ From install to a gated, reported evaluation",
        "subtitle": "Real output of guage-kit 0.1.1: a starter suite, twenty-two metrics with 95% intervals, a CI gate, and reports.",
        "theme": THEME,
        "rows": 26,
        "steps": [
            {"title": "Install", "text": "One package from PyPI. No model, account or network needed to start."},
            {"title": "Scaffold", "text": "A starter guage.yaml and a sample dataset. Never overwrites."},
            {"title": "Evaluate", "text": "Metrics chosen from the fields you have, each with a bootstrap interval."},
            {"title": "Gate", "text": "Rules decided by Ananke Plexus: PASS, WARN, REVIEW or BLOCK, with an exit code."},
            {"title": "Report", "text": "One offline HTML report, plus JUnit and Markdown for CI."},
        ],
        "session": [
            {"cmd": "pip install guage-kit", "step": 0, "out": [{"text": "Successfully installed … guage-kit-0.1.1 …", "tone": "muted"}]},
            {"cmd": "guage init", "step": 1, "out": [
                "✓ wrote guage.yaml",
                "✓ wrote data/sample.jsonl",
                {"text": "Next: guage run  (then open reports/guage-report.html)", "tone": "muted"},
            ]},
            {"cmd": "guage run", "step": 2, "out": [
                {"text": "my-evaluation · 12 samples", "tone": "muted"},
                {"text": " metric                  value   95% CI           n", "tone": "muted"},
                " faithfulness ↑          0.750   0.500 – 1.000   12",
                " recall@5 ↑              1.000   1.000 – 1.000   12",
                " ndcg@10 ↑               0.782   0.631 – 0.922   12",
                " answer_correctness ↑    0.792   0.542 – 1.000   12",
                " pii_leakage ↓           0.000   0.000 – 0.000   12",
                " latency_p95 ↓         786.695   733.456 – 793.900   12",
                {"text": " … 16 more metrics", "tone": "muted"},
            ]},
            {"cmd": "", "step": 3, "out": [
                {"text": "Gate: PASS", "tone": "ok"},
                "  ✓ faithfulness: 0.75 meets ≥ 0.7",
                "  ✓ recall@5: 1 meets ≥ 0.8",
            ]},
            {"cmd": "", "step": 4, "out": [
                {"text": "html: reports/guage-report.html", "tone": "accent"},
                {"text": "junit: reports/guage-junit.xml", "tone": "muted"},
                {"text": "markdown: reports/guage-summary.md", "tone": "muted"},
            ]},
        ],
    },
    {
        "id": "walkthrough-compare",
        "title": "🧪 Did version 2 really get better?",
        "subtitle": "guage compare pairs the samples, bootstraps the difference and corrects for testing many metrics at once (Holm).",
        "theme": THEME,
        "rows": 19,
        "steps": [
            {"title": "Two real runs", "text": "guage demo evaluates two versions of a RAG assistant offline."},
            {"title": "Paired comparison", "text": "Same samples, both versions: Δ, a 95% interval and a permutation test."},
            {"title": "Honest verdicts", "text": "Improved only when the corrected p-value says so; otherwise inconclusive."},
            {"title": "CI-ready", "text": "--fail-on-regression exits 1 when any metric regressed significantly."},
        ],
        "session": [
            {"cmd": "guage demo", "step": 0, "out": [
                "✓ wrote demo/support-assistant-v1.html",
                "✓ wrote demo/support-assistant-v1-vs-v2.html",
                {"text": "Open demo/support-assistant-v1-vs-v2.html in a browser.", "tone": "muted"},
            ]},
            {"cmd": "guage compare demo/runs/rag_v1_run.json demo/runs/rag_v2_run.json --fail-on-regression", "step": 1, "out": [
                {"text": " metric             before   after    Δ       p (Holm)", "tone": "muted"},
            ]},
            {"cmd": "", "step": 2, "out": [
                {"text": " faithfulness       0.549    0.822    0.273   0.009     improved", "tone": "ok"},
                {"text": " context_precision  0.586    0.829    0.243   0.009     improved", "tone": "ok"},
                {"text": " mrr                0.636    0.845    0.208   0.009     improved", "tone": "ok"},
                {"text": " judge_correctness  0.709    0.894    0.185   0.050     improved", "tone": "ok"},
                {"text": " recall@3           0.681    0.875    0.194   0.065     inconclusive", "tone": "warn"},
                {"text": " answer_relevancy   0.423    0.437    0.014   0.219     inconclusive", "tone": "warn"},
                {"text": " pii_leakage        0.000    0.000    0.000   1.000     unchanged", "tone": "muted"},
            ]},
            {"cmd": "echo $?", "step": 3, "out": ["0"]},
        ],
    },
]
