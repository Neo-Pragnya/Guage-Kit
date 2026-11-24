"""How Guage Kit evaluates: an animated concept flow for the README.

Rendered with the marvellous-aws-architecture-docs skill (cards + live numbered flows, no cloud icons):

    python <Skills>/marvellous-aws-architecture-docs/scripts/build_arch.py assets/readme/src/flow.py --out /tmp/guage-flow --no-stages --no-html
    cp /tmp/guage-flow/svg/guage-flow.svg assets/readme/
"""
from archlib import Flow, Node, Spec

INK, TEAL, AMBER, CORAL, VIOLET, SKY, GREEN = "#0F1A1F", "#0F6E66", "#B45309", "#C2410C", "#6D28D9", "#0369A1", "#047857"


def card(id, title, body, x, y, color, w=1.8, sub="", **kw):
    return Node(id, None, title, sub=sub, x=x, y=y, body=body, color=color, w=w, **kw)


SPECS = [Spec(
    id="guage-flow", title="How Guage Kit measures a system",
    subtitle="Samples in, a verdict and a report out. Every number carries an interval; the gate is decided by Ananke Plexus.",
    cols=8.4, rows=3.3,
    nodes=[
        card("data", "Dataset", ["JSONL · JSON · YAML · CSV,", "or generated from your docs"], 0.95, 0.35, SKY),
        card("target", "Your system (optional)", ["module:function or a model spec", "outputs, contexts, tool calls,", "latency and tokens recorded"], 0.95, 2.35, VIOLET),
        card("metrics", "167 metrics", ["90 native: text, RAG, retrieval,", "classification, safety, agents …", "77 Ananke trace evaluators"], 3.45, 0.0, TEAL, sub="deterministic"),
        card("judge", "LLM judges", ["11 anchored criteria or a rubric", "cached · both orders · calibrated", "Claude, OpenAI-compatible, Ollama"], 3.45, 1.4, AMBER, sub="optional"),
        card("stats", "Statistics", ["95% bootstrap intervals", "paired permutation tests", "Holm correction · effect sizes"], 3.45, 2.8, INK),
        card("gate", "Quality gate", ["min · max · max_drop rules", "PASS · WARN · REVIEW · BLOCK", "decided by Ananke Plexus"], 6.05, 0.55, CORAL, w=1.9),
        card("out", "Reports", ["one offline HTML file", "JUnit · Markdown · run.json", "Ananke evidence bundle"], 6.05, 2.55, GREEN, w=1.9),
    ],
    flows=[
        Flow(1, "data", "target", "Each sample's input goes to your system, which returns an output (or the dataset already has one)", packet="input"),
        Flow(2, "target", "metrics", "Every applicable metric scores every sample; what a metric needs decides whether it runs", packet="output"),
        Flow(3, "metrics", "judge", "Criteria that need judgement go to a judge, with sample text fenced as untrusted", packet="grade"),
        Flow(4, "judge", "stats", "Per-sample scores become a mean with a 95% interval; two runs become a paired test", packet="CI"),
        Flow(5, "stats", "gate", "Your rules are checked against the numbers; a missing value is never a silent pass", packet="rules"),
        Flow(6, "gate", "out", "The verdict, every score and every sample land in reports you can open anywhere", packet="verdict"),
    ],
)]
