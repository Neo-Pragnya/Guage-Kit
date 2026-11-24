"""Regressions for the metric bugs found while writing the metric cards (each compared with a reference where one exists)."""

from __future__ import annotations

import math

import pytest
import sacrebleu
from rouge_score import rouge_scorer

from guage_kit.core.sample import Sample, Usage
from guage_kit.errors import GuageError
from guage_kit.metrics.registry import resolve


def s(**kw: object) -> Sample:
    return Sample.model_validate({"id": "1", "input": kw.pop("input", "q"), **kw})


def score(name: str, sample: Sample, **params: object) -> float | None:
    return resolve({"name": name, "params": params}).score(sample).value


def test_chrf_ignores_every_kind_of_whitespace() -> None:
    hyp, ref = "the cat\nsat\ton the mat", "the cat sat on the mat"
    want = sacrebleu.sentence_chrf(hyp, [ref]).score / 100
    assert math.isclose(score("chrf", s(output=hyp, expected=ref)) or 0, want, abs_tol=1e-4)


def test_chrf_pp_splits_leading_punctuation_like_sacrebleu() -> None:
    hyp, ref = '"Hello," she said (quietly).', "Hello, she said quietly."
    want = sacrebleu.sentence_chrf(hyp, [ref], word_order=2).score / 100
    assert math.isclose(score("chrf_pp", s(output=hyp, expected=ref)) or 0, want, abs_tol=1e-4)


def test_corpus_chrf_uses_the_best_reference() -> None:
    hyps = ["the cat sat on the mat", "a fast brown fox"]
    refs = [
        ["a feline was sitting", "the cat sat on the mat"],
        ["the quick brown fox", "a fast brown fox"],
    ]
    samples = [s(output=h, references=r) for h, r in zip(hyps, refs, strict=True)]
    value = resolve("corpus_chrf").compute(samples).value
    # sacreBLEU's multi-reference corpus chrF picks each sentence's best reference; here both are exact copies
    assert value is not None and math.isclose(value, 1.0, abs_tol=1e-9)


def test_rouge_lsum_treats_line_breaks_as_sentences() -> None:
    pred = "the cat sat on the mat\nthe dog barked loudly"
    ref = "the dog barked loudly\nthe cat sat on the mat"
    want = rouge_scorer.RougeScorer(["rougeLsum"]).score(ref, pred)["rougeLsum"].fmeasure
    assert math.isclose(score("rougeLsum", s(output=pred, expected=ref)) or 0, want, abs_tol=1e-4)


def test_numbers_in_a_list_are_separate() -> None:
    assert score("numeric_match", s(output="2", expected="1,2,3")) == 1.0
    assert score("numeric_match", s(output="1234", expected="1,234")) == 1.0


def test_grouped_citations_count() -> None:
    sample = s(
        output="Paris is the capital of France [1, 2]. It lies on the Seine [1].",
        contexts=[
            "Paris is the capital of France and lies on the Seine.",
            "The capital of France is Paris.",
        ],
    )
    assert score("citation_coverage", sample) == 1.0
    acc = resolve("citation_accuracy").score(sample)
    assert acc.value == 1.0 and len(acc.details["citations"]) == 3


def test_context_relevance_skips_a_question_without_content_words() -> None:
    r = resolve("context_relevance").score(s(input="What is it?", contexts=["Paris is in France."]))
    assert r.skipped


@pytest.mark.parametrize(
    "name", ["precision", "hit_rate", "recall", "mrr", "ndcg", "average_precision"]
)
def test_ranking_metrics_skip_samples_without_relevant_ids(name: str) -> None:
    r = resolve(name).score(s(retrieved_ids=["a", "b"], relevance={"a": 0}))
    assert r.skipped, name


def test_refusal_with_typographic_apostrophes() -> None:
    assert score("refusal", s(output="I’m sorry, but I can’t help with that.")) == 1.0


def test_pii_echo_check_compares_full_values() -> None:
    sample = s(
        input="My email is jo@example.com", output="Contact jo-other-person@example.com instead."
    )
    assert score("pii_leakage", sample) == 1.0
    assert (
        score(
            "pii_leakage",
            s(input="My email is jo@example.com", output="I will write to jo@example.com."),
        )
        == 0.0
    )


def test_cost_needs_split_token_counts() -> None:
    prices = {"m": [3.0, 15.0]}
    only_total = s(usage=Usage(total_tokens=1000), metadata={"model": "m"})
    assert resolve({"name": "cost_usd", "params": {"prices": prices}}).score(only_total).skipped
    split = s(usage=Usage(prompt_tokens=1000, completion_tokens=100), metadata={"model": "m"})
    assert math.isclose(score("cost_usd", split, prices=prices) or 0, (3000 + 1500) / 1e6)


def test_percentile_outside_range_is_a_clean_error() -> None:
    samples = [s(latency_ms=v) for v in (10.0, 20.0, 30.0)]
    with pytest.raises(GuageError):
        resolve("latency_p95@101").compute(samples)
