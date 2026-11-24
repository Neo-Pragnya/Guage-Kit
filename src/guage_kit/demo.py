"""A complete, offline demonstration: ``guage demo`` (and the website's live reports).

It evaluates three systems around a fictional notes app, Lumen Notes, with deterministic simulated behaviour so
every number is reproducible without a model:

- a **support assistant** (RAG) in two versions, compared with paired statistics (v2 retrieves better and stops
  inventing details);
- a **tool-using agent** that books, looks up and refunds, scored on tool choice, arguments and trajectory (by Guage Kit
  and by Ananke's evaluators);
- an **intent classifier** with probabilities, scored on accuracy, F1 and calibration.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from pathlib import Path
from typing import Any

from guage_kit.core.dataset import Dataset
from guage_kit.core.results import RunResult
from guage_kit.core.sample import Sample, ToolCall, Usage

DOCS: dict[str, str] = {
    "kb-sync": "Lumen Notes syncs across devices every 30 seconds when you are online. Offline edits are kept on the device and uploaded when the connection returns.",
    "kb-export": "You can export a notebook as Markdown, PDF or HTML from the notebook menu. Exports include attachments up to 25 MB each.",
    "kb-pricing": "Lumen Notes Free includes 3 notebooks and 1 GB of storage. Lumen Notes Pro costs 6 dollars per month and includes unlimited notebooks and 100 GB of storage.",
    "kb-sharing": "Shared notebooks can be opened by up to 20 collaborators. Owners can grant view, comment or edit access to each person.",
    "kb-security": "Notes are encrypted in transit with TLS 1.3 and at rest with AES-256. End-to-end encryption is available for Pro notebooks marked private.",
    "kb-refund": "Annual Pro subscriptions can be refunded in full within 14 days of purchase. Monthly plans are not refunded but can be cancelled at any time.",
    "kb-tags": "Tags are created by typing a hash sign before a word. A note can carry up to 50 tags, and tags can be nested with a slash.",
    "kb-search": "Search looks inside note text, attachments and handwriting. Handwriting search supports English, Spanish and German.",
    "kb-backup": "Pro accounts keep a version history of 90 days. Free accounts keep 7 days of history. Deleted notes stay in the trash for 30 days.",
    "kb-import": "Notes can be imported from Markdown folders, plain text files and ENEX archives. Imports keep creation dates and tags.",
    "kb-offline": "Offline mode is available on desktop and mobile. On mobile, choose which notebooks to keep offline from the notebook settings.",
    "kb-api": "The Lumen Notes API allows 600 requests per minute per token. Tokens are created in account settings and can be revoked at any time.",
}

QA: list[tuple[str, str, str, str, str]] = [
    # id, question, answer, relevant doc, difficulty
    (
        "q01",
        "How often does Lumen Notes sync?",
        "Every 30 seconds when you are online.",
        "kb-sync",
        "easy",
    ),
    (
        "q02",
        "What happens to edits I make offline?",
        "They are kept on the device and uploaded when the connection returns.",
        "kb-sync",
        "easy",
    ),
    (
        "q03",
        "Which formats can I export a notebook to?",
        "Markdown, PDF or HTML.",
        "kb-export",
        "easy",
    ),
    ("q04", "How big can attachments in an export be?", "Up to 25 MB each.", "kb-export", "medium"),
    ("q05", "How much does Pro cost?", "6 dollars per month.", "kb-pricing", "easy"),
    (
        "q06",
        "How much storage does the free plan include?",
        "1 GB of storage and 3 notebooks.",
        "kb-pricing",
        "easy",
    ),
    (
        "q07",
        "How many people can collaborate on a shared notebook?",
        "Up to 20 collaborators.",
        "kb-sharing",
        "easy",
    ),
    (
        "q08",
        "What access levels can owners grant?",
        "View, comment or edit access.",
        "kb-sharing",
        "medium",
    ),
    ("q09", "How are notes encrypted at rest?", "With AES-256.", "kb-security", "medium"),
    (
        "q10",
        "Is end-to-end encryption available?",
        "Yes, for Pro notebooks marked private.",
        "kb-security",
        "hard",
    ),
    (
        "q11",
        "Can I get a refund on an annual plan?",
        "Yes, in full within 14 days of purchase.",
        "kb-refund",
        "medium",
    ),
    (
        "q12",
        "Are monthly plans refundable?",
        "No, but they can be cancelled at any time.",
        "kb-refund",
        "hard",
    ),
    ("q13", "How do I create a tag?", "Type a hash sign before a word.", "kb-tags", "easy"),
    ("q14", "How many tags can one note have?", "Up to 50 tags.", "kb-tags", "medium"),
    (
        "q15",
        "Can search read my handwriting?",
        "Yes, in English, Spanish and German.",
        "kb-search",
        "hard",
    ),
    ("q16", "How long is version history kept on Pro?", "90 days.", "kb-backup", "medium"),
    ("q17", "How long do deleted notes stay in the trash?", "30 days.", "kb-backup", "easy"),
    (
        "q18",
        "Which files can I import?",
        "Markdown folders, plain text files and ENEX archives.",
        "kb-import",
        "medium",
    ),
    (
        "q19",
        "Do imports keep my tags?",
        "Yes, imports keep creation dates and tags.",
        "kb-import",
        "hard",
    ),
    (
        "q20",
        "How do I keep notebooks offline on my phone?",
        "Choose them in the notebook settings.",
        "kb-offline",
        "hard",
    ),
    (
        "q21",
        "What is the API rate limit?",
        "600 requests per minute per token.",
        "kb-api",
        "medium",
    ),
    ("q22", "Where do I create an API token?", "In account settings.", "kb-api", "easy"),
    ("q23", "How long is history kept on the free plan?", "7 days.", "kb-backup", "hard"),
    ("q24", "Can tags be nested?", "Yes, with a slash.", "kb-tags", "hard"),
]

HALLUCINATIONS = [
    "Priority support is included for all customers.",
    "This feature was introduced in 2019 by the founding team.",
    "You can also ask your administrator to raise the limit to 10,000.",
    "A browser extension is required for this to work.",
]


def _rank(rng: random.Random, relevant: str, quality: float) -> list[str]:
    others = [d for d in DOCS if d != relevant]
    rng.shuffle(others)
    ranking = others[:4]
    pos = 0 if rng.random() < quality else rng.randint(1, 4) if rng.random() < 0.8 else None
    if pos is not None:
        ranking.insert(pos, relevant)
    return ranking[:5]


def rag_dataset(version: str = "v2", seed: int = 7) -> Dataset:
    """The support-assistant dataset with the simulated outputs of ``v1`` or ``v2``."""
    rng = random.Random(f"{seed}-{version}")
    quality = {"v1": 0.55, "v2": 0.85}[version]
    invent = {"v1": 0.35, "v2": 0.08}[version]
    samples = []
    phrasings: tuple[Callable[[str], str], ...] = (
        lambda q: q,
        lambda q: "Quick question: " + q[0].lower() + q[1:],
        lambda q: "Could you tell me this? " + q,
    )
    rows = [
        (f"{qid}{'abc'[i]}", f(q), a, rel, diff)
        for qid, q, a, rel, diff in QA
        for i, f in enumerate(phrasings)
    ]
    for qid, q, a, rel, diff in rows:
        ranking = _rank(rng, rel, quality - (0.15 if diff == "hard" else 0.0))
        contexts = [DOCS[d] for d in ranking[:3]]
        found = rel in ranking[:3]
        if found:
            answer = a
            if version == "v2" and rng.random() < 0.5:
                answer = f"{a} [{ranking.index(rel) + 1}]"
        else:
            answer = "I could not find that in the help centre, but it is usually configurable in settings."
        if rng.random() < invent:
            answer = answer + " " + rng.choice(HALLUCINATIONS)
        latency = rng.gauss(820 if version == "v1" else 640, 120)
        samples.append(
            Sample(
                id=qid,
                input=q,
                output=answer,
                expected=a,
                contexts=contexts,
                retrieved_ids=ranking,
                relevant_ids=[rel],
                latency_ms=round(max(120.0, latency), 1),
                usage=Usage(
                    prompt_tokens=rng.randint(380, 900),
                    completion_tokens=rng.randint(20, 90),
                    cost_usd=None,
                ),
                tags=[diff, rel.removeprefix("kb-")],
                metadata={"difficulty": diff, "model": f"support-{version}"},
            )
        )
    return Dataset(samples, name=f"support-assistant-{version}")


AGENT_TASKS: list[tuple[str, str, list[ToolCall]]] = [
    (
        "a01",
        "Refund order 1042, it arrived broken.",
        [
            ToolCall(name="lookup_order", arguments={"order_id": "1042"}),
            ToolCall(name="issue_refund", arguments={"order_id": "1042", "reason": "damaged"}),
        ],
    ),
    (
        "a02",
        "What's the status of order 2210?",
        [ToolCall(name="lookup_order", arguments={"order_id": "2210"})],
    ),
    (
        "a03",
        "Book a demo for Acme on Friday at 10.",
        [
            ToolCall(name="check_calendar", arguments={"day": "friday"}),
            ToolCall(
                name="book_meeting", arguments={"company": "acme", "day": "friday", "time": "10:00"}
            ),
        ],
    ),
    (
        "a04",
        "Cancel my subscription.",
        [
            ToolCall(name="lookup_account", arguments={}),
            ToolCall(name="cancel_subscription", arguments={}),
        ],
    ),
    (
        "a05",
        "Change the email on my account to sam@example.org.",
        [
            ToolCall(name="lookup_account", arguments={}),
            ToolCall(name="update_email", arguments={"email": "sam@example.org"}),
        ],
    ),
    (
        "a06",
        "Refund order 3301 because it never arrived.",
        [
            ToolCall(name="lookup_order", arguments={"order_id": "3301"}),
            ToolCall(
                name="issue_refund", arguments={"order_id": "3301", "reason": "not delivered"}
            ),
        ],
    ),
    (
        "a07",
        "Is there a meeting slot on Monday?",
        [ToolCall(name="check_calendar", arguments={"day": "monday"})],
    ),
    (
        "a08",
        "Where is order 5512?",
        [ToolCall(name="lookup_order", arguments={"order_id": "5512"})],
    ),
    (
        "a09",
        "Book a call with Globex on Tuesday at 15:30.",
        [
            ToolCall(name="check_calendar", arguments={"day": "tuesday"}),
            ToolCall(
                name="book_meeting",
                arguments={"company": "globex", "day": "tuesday", "time": "15:30"},
            ),
        ],
    ),
    (
        "a10",
        "Refund order 7781.",
        [
            ToolCall(name="lookup_order", arguments={"order_id": "7781"}),
            ToolCall(
                name="issue_refund", arguments={"order_id": "7781", "reason": "customer request"}
            ),
        ],
    ),
    (
        "a11",
        "Upgrade me to the annual plan.",
        [
            ToolCall(name="lookup_account", arguments={}),
            ToolCall(name="change_plan", arguments={"plan": "annual"}),
        ],
    ),
    (
        "a12",
        "What did I order last week?",
        [
            ToolCall(name="lookup_account", arguments={}),
            ToolCall(name="list_orders", arguments={"since_days": 7}),
        ],
    ),
]


def agent_dataset(seed: int = 11) -> Dataset:
    rng = random.Random(seed)
    samples = []
    for aid, task, expected in AGENT_TASKS:
        calls = [c.model_copy(deep=True) for c in expected]
        r = rng.random()
        if r < 0.15 and len(calls) > 1:
            calls = calls[1:]  # skipped the lookup
        elif r < 0.3:
            calls.insert(
                0, calls[0].model_copy(update={"error": "timeout"})
            )  # failed once, retried
        elif r < 0.4 and calls[-1].arguments:
            k = next(iter(calls[-1].arguments))
            calls[-1] = calls[-1].model_copy(
                update={"arguments": {**calls[-1].arguments, k: "wrong"}}
            )
        elif r < 0.48:
            calls.append(ToolCall(name="lookup_order", arguments={"order_id": "0000"}))  # wandered
        success = [c.name for c in calls if not c.error] == [c.name for c in expected] and all(
            a.arguments == b.arguments
            for a, b in zip([c for c in calls if not c.error], expected, strict=False)
        )
        samples.append(
            Sample(
                id=aid,
                input=task,
                output="Done." if success else "I have done what I could; please check the result.",
                tool_calls=calls,
                expected_tool_calls=expected,
                latency_ms=round(rng.uniform(900, 4200), 1),
                usage=Usage(
                    prompt_tokens=rng.randint(1200, 4000), completion_tokens=rng.randint(80, 400)
                ),
                tags=[expected[-1].name],
                metadata={
                    "success": success,
                    "ananke": {"max_consecutive": 2, "denied": ["delete_account"]},
                },
            )
        )
    return Dataset(samples, name="support-agent")


INTENTS = ["billing", "bug", "feature_request", "account", "other"]
INTENT_TEXT = {
    "billing": [
        "I was charged twice this month",
        "Can I get an invoice for March?",
        "Why did my price go up?",
        "Refund my last payment please",
    ],
    "bug": [
        "The app crashes when I open a PDF",
        "Sync is stuck at 99 percent",
        "Search returns nothing for handwriting",
        "Export to HTML loses images",
    ],
    "feature_request": [
        "Please add a dark theme for printing",
        "Could you support LaTeX formulas?",
        "I'd love calendar integration",
        "Add folders inside notebooks",
    ],
    "account": [
        "How do I change my password?",
        "I can't log in with Google",
        "Delete my account",
        "Update the email on my profile",
    ],
    "other": [
        "Do you have a student discount?",
        "Who founded Lumen?",
        "Is there a community forum?",
        "Love the app, thanks!",
    ],
}


def classifier_dataset(seed: int = 3) -> Dataset:
    rng = random.Random(seed)
    samples = []
    i = 0
    for gold, texts in INTENT_TEXT.items():
        for t in texts * 3:
            i += 1
            correct = rng.random() < (0.9 if gold != "other" else 0.6)
            pred = gold if correct else rng.choice([x for x in INTENTS if x != gold])
            top = (
                rng.uniform(0.55, 0.97) if correct else rng.uniform(0.45, 0.9)
            )  # slightly over-confident when wrong
            rest = (1 - top) / (len(INTENTS) - 1)
            probs = {lab: round(top if lab == pred else rest, 4) for lab in INTENTS}
            samples.append(
                Sample(
                    id=f"c{i:03d}",
                    input=t,
                    expected=gold,
                    label=pred,
                    probabilities=probs,
                    tags=[gold],
                )
            )
    return Dataset(samples, name="intent-classifier")


RAG_METRICS: list[Any] = [
    "contains",
    "token_f1",
    {"name": "faithfulness", "threshold": 0.7},
    "answer_relevancy",
    "context_recall",
    "context_precision",
    "recall@3",
    "mrr",
    "ndcg@5",
    {"name": "judge", "params": {"criterion": "correctness"}, "as": "judge_correctness"},
    "latency_p95",
    "pii_leakage",
]
RAG_GATES = [
    {"metric": "faithfulness", "min": 0.8},
    {"metric": "recall@3", "min": 0.75, "on_fail": "warn"},
    {"metric": "latency_p95", "max": 1200, "on_fail": "warn"},
]
AGENT_METRICS: list[Any] = [
    "tool_call_f1",
    "tool_args_accuracy",
    "tool_sequence_match",
    "tool_calls_exact",
    "tool_error_rate",
    "redundant_tool_calls",
    "goal_success",
    "ananke.trajectory.loop_detection",
    "ananke.tool_use.tool_denylist",
    "ananke.trajectory.required_step",
    "latency_p95",
]
CLASSIFIER_METRICS = [
    "accuracy",
    "f1",
    "balanced_accuracy",
    "cohen_kappa",
    "mcc",
    "ece",
    "brier",
    "selective_auroc",
]


def run_demo(out_dir: str | Path, *, profile: str = "private") -> dict[str, Path]:
    """Evaluate the three systems and write their reports into ``out_dir``. Returns the written files."""
    from guage_kit.reports import markdown, write_report
    from guage_kit.runner.compare import compare
    from guage_kit.runner.evaluate import evaluate

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    v1 = evaluate(
        rag_dataset("v1"),
        RAG_METRICS,
        judge="heuristic",
        gates=RAG_GATES,
        slices=["difficulty"],
        name="Support assistant v1",
    )
    v2 = evaluate(
        rag_dataset("v2"),
        RAG_METRICS,
        judge="heuristic",
        gates=RAG_GATES,
        slices=["difficulty"],
        name="Support assistant v2",
    )
    cmp = compare(v1, v2)
    agent = evaluate(
        agent_dataset(),
        AGENT_METRICS,
        gates=[
            {"metric": "tool_call_f1", "min": 0.9},
            {"metric": "goal_success", "min": 0.7, "on_fail": "review"},
        ],
        slices=["tags"],
        name="Support agent",
    )
    clf = evaluate(
        classifier_dataset(),
        CLASSIFIER_METRICS,
        gates=[{"metric": "f1", "min": 0.8}, {"metric": "ece", "max": 0.1, "on_fail": "warn"}],
        slices=["tags"],
        name="Intent classifier",
    )
    files = {
        "rag_v1": write_report(v1, out / "support-assistant-v1.html", profile=profile),
        "rag_compare": write_report(
            v2, out / "support-assistant-v1-vs-v2.html", comparison=cmp, profile=profile
        ),
        "agent": write_report(agent, out / "support-agent.html", profile=profile),
        "classifier": write_report(clf, out / "intent-classifier.html", profile=profile),
    }
    (out / "summary.md").write_text(
        "\n".join(markdown(r, c) for r, c in ((v2, cmp), (agent, None), (clf, None))),
        encoding="utf-8",
    )
    files["summary"] = out / "summary.md"
    for name, run in (
        ("rag_v1_run", v1),
        ("rag_v2_run", v2),
        ("agent_run", agent),
        ("classifier_run", clf),
    ):
        files[name] = run.save(out / "runs" / f"{name}.json")
    return files


def demo_runs() -> dict[str, RunResult]:
    from guage_kit.runner.evaluate import evaluate

    return {
        "rag_v1": evaluate(
            rag_dataset("v1"),
            RAG_METRICS,
            judge="heuristic",
            gates=RAG_GATES,
            name="Support assistant v1",
        ),
        "rag_v2": evaluate(
            rag_dataset("v2"),
            RAG_METRICS,
            judge="heuristic",
            gates=RAG_GATES,
            name="Support assistant v2",
        ),
    }


__all__ = ["agent_dataset", "classifier_dataset", "demo_runs", "rag_dataset", "run_demo"]
