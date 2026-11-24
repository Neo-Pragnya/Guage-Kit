"""Every native metric has a complete card, and every worked example in a card is what the metric really returns."""

from __future__ import annotations

import math
from typing import Any

import pytest

from guage_kit.core.sample import Sample
from guage_kit.judges import HeuristicJudge
from guage_kit.metrics.cards import CARD_FIELDS, REQUIRED_FIELDS, load_cards
from guage_kit.metrics.registry import MetricContext, get_metric, list_metrics, resolve
from guage_kit.metrics.semantic import HashingEmbedder

NATIVE = sorted(m["name"] for m in list_metrics() if m["source"] != "ananke-plexus")
CARDS = load_cards()


def test_every_native_metric_has_a_card() -> None:
    missing = [n for n in NATIVE if n not in CARDS]
    assert not missing, f"metrics without a card: {missing}"
    unknown = [n for n in CARDS if n not in NATIVE]
    assert not unknown, f"cards for metrics that do not exist: {unknown}"


@pytest.mark.parametrize("name", sorted(CARDS))
def test_card_is_complete(name: str) -> None:
    card = CARDS[name]
    extra = set(card) - set(CARD_FIELDS) - {"family_file"}
    assert not extra, f"{name}: unknown fields {extra}"
    for f in REQUIRED_FIELDS:
        assert card.get(f) not in (None, ""), f"{name}: missing {f}"
    assert isinstance(card["pitfalls"], list) and card["pitfalls"]
    for ref in card["references"]:
        assert ref.get("citation"), f"{name}: reference without a citation"
        assert str(ref.get("url", "https://")).startswith("https://"), f"{name}: {ref}"
    info = get_metric(name)
    documented = set(card.get("params") or {})
    declared = set(info.params)
    assert documented == declared, f"{name}: params documented {documented}, declared {declared}"
    for other in card.get("related") or []:
        assert other in NATIVE or other.startswith("ananke."), (
            f"{name}: related {other!r} is unknown"
        )
    assert info.family == card["family_file"] or info.family.startswith(card["family_file"])


def _sample(i: int, raw: dict[str, Any]) -> Sample:
    return Sample.model_validate({"id": str(i), "input": raw.pop("input", "q"), **raw})


@pytest.mark.parametrize("name", sorted(n for n in CARDS if CARDS[n].get("example")))
def test_card_example_is_true(name: str) -> None:
    ex = CARDS[name]["example"]
    samples = [_sample(i, dict(s)) for i, s in enumerate(ex["samples"])]
    bound = resolve({"name": name, "params": ex.get("params") or {}})
    ctx = MetricContext(judge=HeuristicJudge(), embedder=HashingEmbedder())
    if bound.info.level == "corpus":
        value = bound.compute(samples, ctx).value
    else:
        assert len(samples) == 1, f"{name}: a sample metric's example has one sample"
        score = bound.score(samples[0], ctx)
        assert score.error is None and not score.skipped, f"{name}: {score}"
        value = score.value
    want = ex["value"]
    assert value is not None and math.isclose(value, want, abs_tol=ex.get("tolerance", 1e-3)), (
        f"{name}: example says {want}, metric returns {value}"
    )


def test_evaluator_cards_match_ananke() -> None:
    from guage_kit.metrics.cards import EVALUATOR_FIELDS, load_evaluator_cards

    ananke = {m["name"]: m for m in list_metrics() if m["source"] == "ananke-plexus"}
    cards = load_evaluator_cards()
    assert not set(cards) - set(ananke), f"cards for unknown evaluators: {set(cards) - set(ananke)}"
    for name, card in cards.items():
        assert set(card) <= set(EVALUATOR_FIELDS), (
            f"{name}: unknown fields {set(card) - set(EVALUATOR_FIELDS)}"
        )
        for f in ("summary", "method", "passes_when"):
            assert card.get(f), f"{name}: missing {f}"
        assert set(card.get("arguments") or {}) == set(ananke[name]["params"]), f"{name}: arguments"
        for ref in card.get("references") or []:
            assert ref.get("citation") and str(ref.get("url", "https://")).startswith("https://")
