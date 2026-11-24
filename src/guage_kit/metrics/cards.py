"""Metric cards: the long-form documentation of every native metric, shipped with the package.

One YAML file per family under ``guage_kit/metrics/cards/``. Each card says what the metric measures, how it is
computed, how to read it, its pitfalls, a worked example (checked by the test suite against the real metric) and
the papers or specifications that define it. ``guage metrics show <name>`` prints the card, and
``scripts/gen_metric_docs.py`` renders them into the metric reference.

Card fields (all text is Markdown):

``summary``     one sentence, plain language
``measures``    the question the metric answers
``method``      how it is computed, step by step
``formula``     the formula in plain-text math (rendered as a code block)
``inputs``      which sample fields it reads and how
``params``      {name: explanation} for every configurable parameter
``interpret``   how to read the number, what good looks like
``use_when``    [situations it suits]
``pitfalls``    [ways it misleads]
``example``     {samples: [...], params: {...}, value: float, tolerance: float, note: str}
``related``     [other metric names]
``references``  [{citation: str, url: str}]
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from typing import Any

import yaml

CARD_FIELDS = (
    "summary",
    "measures",
    "method",
    "formula",
    "inputs",
    "params",
    "interpret",
    "use_when",
    "pitfalls",
    "example",
    "related",
    "references",
)
REQUIRED_FIELDS = ("summary", "measures", "method", "inputs", "interpret", "pitfalls", "references")


@lru_cache(maxsize=1)
def load_cards() -> dict[str, dict[str, Any]]:
    """Every card, keyed by metric name."""
    cards: dict[str, dict[str, Any]] = {}
    folder = resources.files("guage_kit.metrics") / "cards"
    for entry in sorted(folder.iterdir(), key=lambda e: e.name):
        if not entry.name.endswith(".yaml"):
            continue
        data = yaml.safe_load(entry.read_text(encoding="utf-8")) or {}
        for name, card in data.items():
            if name in cards:
                raise ValueError(f"metric card {name!r} is defined twice")
            cards[name] = {"family_file": entry.name.removesuffix(".yaml"), **card}
    return cards


EVALUATOR_FIELDS = (
    "summary",
    "method",
    "arguments",
    "passes_when",
    "use_when",
    "pitfalls",
    "example",
    "references",
)


@lru_cache(maxsize=1)
def load_evaluator_cards() -> dict[str, dict[str, Any]]:
    """Cards for the Ananke Plexus evaluators (``ananke.*`` metrics), keyed by evaluator id.

    Written from Ananke Plexus's source (one YAML file per dimension group under ``cards/ananke/``): what the evaluator reads from the trace, when it passes, and what its
    arguments mean. ``example`` is a suite snippet (YAML text), not executed. An evaluator added by a newer Ananke
    Plexus release has no card until one is written; the reference then shows its one-line description.
    """
    folder = resources.files("guage_kit.metrics") / "cards" / "ananke"
    cards: dict[str, dict[str, Any]] = {}
    for entry in sorted(folder.iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".yaml"):
            data = yaml.safe_load(entry.read_text(encoding="utf-8")) or {}
            for k, v in data.items():
                if str(k) in cards:
                    raise ValueError(f"evaluator card {k!r} is defined twice")
                cards[str(k)] = dict(v)
    return cards


def get_card(name: str) -> dict[str, Any] | None:
    """The card for one metric (native or Ananke evaluator), or None (plugin metrics have none)."""
    return load_cards().get(name) or load_evaluator_cards().get(name)


__all__ = [
    "CARD_FIELDS",
    "EVALUATOR_FIELDS",
    "REQUIRED_FIELDS",
    "get_card",
    "load_cards",
    "load_evaluator_cards",
]
