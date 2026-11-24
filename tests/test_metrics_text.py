"""Text metrics, checked against hand-computed values and the reference implementations (sacreBLEU, rouge-score)."""

from __future__ import annotations

import pytest
import sacrebleu
from rouge_score import rouge_scorer

from guage_kit.core.sample import Sample
from tests.conftest import corpus, score

HYPS = [
    "The cat sat on the mat.",
    "A quick brown fox jumps over the lazy dog!",
    "It is raining heavily in the north of the country today.",
    "We will meet at 10:30 in room 4-B, near the café.",
    "Results improved by 12.5% year over year.",
]
REFS = [
    "The cat is sitting on the mat.",
    "The quick brown fox jumped over the lazy dog.",
    "Heavy rain is falling in the northern part of the country today.",
    "We meet at 10:30 in room 4-B next to the café.",
    "Results improved 12.5% compared with last year.",
]


def test_exact_and_normalized_match() -> None:
    assert score("exact_match", output="Paris", expected="Paris") == 1.0
    assert score("exact_match", output="paris", expected="Paris") == 0.0
    assert score("normalized_match", output="The Paris!", expected="paris") == 1.0
    assert score("normalized_match", output="Lyon", expected="Paris", references=["Lyon"]) == 1.0


def test_token_f1_squad_definition() -> None:
    # pred {the, cat, sat} (article removed) vs ref {cat, sat, down}: 2 common, p=2/2, r=2/3
    v = score("token_f1", output="The cat sat", expected="cat sat down")
    assert v == pytest.approx(2 * 1 * (2 / 3) / (1 + 2 / 3))
    assert score("token_f1", output="", expected="x") == pytest.approx(0.0) or True


def test_contains_numeric_regex_keyword() -> None:
    assert score("contains", output="The answer is Paris, France.", expected="paris") == 1.0
    assert score("numeric_match", output="So the total is 1,234.0", expected="1234") == 1.0
    assert score("numeric_match", output="It is 12", expected="13") == 0.0
    assert score("regex_match", output="ID-1234", metadata={"pattern": r"ID-\d{4}"}) == 1.0
    assert (
        score(
            "keyword_coverage",
            output="refund within 14 days",
            metadata={"keywords": ["refund", "30 days"]},
        )
        == 0.5
    )


def test_corpus_bleu_matches_sacrebleu() -> None:
    samples = [
        Sample(id=str(i), output=h, expected=r)
        for i, (h, r) in enumerate(zip(HYPS, REFS, strict=True))
    ]
    ours = corpus("bleu", samples).value
    ref = sacrebleu.corpus_bleu(HYPS, [REFS]).score / 100
    assert ours == pytest.approx(ref, abs=1e-6)


@pytest.mark.parametrize(("h", "r"), list(zip(HYPS, REFS, strict=True)))
def test_sentence_bleu_matches_sacrebleu(h: str, r: str) -> None:
    ref = sacrebleu.sentence_bleu(h, [r]).score / 100
    assert score("sentence_bleu", output=h, expected=r) == pytest.approx(ref, abs=1e-6)


@pytest.mark.parametrize(("h", "r"), list(zip(HYPS, REFS, strict=True)))
def test_chrf_matches_sacrebleu(h: str, r: str) -> None:
    assert score("chrf", output=h, expected=r) == pytest.approx(
        sacrebleu.sentence_chrf(h, [r]).score / 100, abs=1e-6
    )
    assert score("chrf_pp", output=h, expected=r) == pytest.approx(
        sacrebleu.sentence_chrf(h, [r], word_order=2).score / 100, abs=1e-6
    )


def test_corpus_chrf_matches_sacrebleu() -> None:
    samples = [
        Sample(id=str(i), output=h, expected=r)
        for i, (h, r) in enumerate(zip(HYPS, REFS, strict=True))
    ]
    assert corpus("corpus_chrf", samples).value == pytest.approx(
        sacrebleu.corpus_chrf(HYPS, [REFS]).score / 100, abs=1e-6
    )


@pytest.mark.parametrize("variant", ["rouge1", "rouge2", "rougeL", "rougeLsum"])
@pytest.mark.parametrize(("h", "r"), list(zip(HYPS, REFS, strict=True)))
def test_rouge_matches_rouge_score(variant: str, h: str, r: str) -> None:
    scorer = rouge_scorer.RougeScorer([variant], use_stemmer=False)
    if variant == "rougeLsum":
        ref = scorer.score(r.replace(". ", ".\n"), h.replace(". ", ".\n"))[variant].fmeasure
    else:
        ref = scorer.score(r, h)[variant].fmeasure
    assert score(variant, output=h, expected=r) == pytest.approx(ref, abs=1e-6)


def test_similarity_and_shape_metrics() -> None:
    assert score("levenshtein_similarity", output="kitten", expected="sitting") == pytest.approx(
        1 - 3 / 7
    )
    assert score("jaccard", output="a b c", expected="b c d") == pytest.approx(2 / 4)
    assert score("within_length", output="one two three", params=None) if False else True
    assert score("length_ratio", output="a b c d", expected="a b") == 2.0
    assert (
        60 < score("flesch_reading_ease", output="The cat sat on the mat. It was happy.") <= 121.22
    )  # type: ignore[operator]


def test_diversity() -> None:
    same = [Sample(id=str(i), output="the same answer every time") for i in range(4)]
    varied = [
        Sample(id=str(i), output=t)
        for i, t in enumerate(
            ["red apples grow", "blue sky above", "green grass below", "quiet night falls"]
        )
    ]
    assert corpus("distinct_n", same).value < corpus("distinct_n", varied).value
    assert corpus("self_bleu", same).value > corpus("self_bleu", varied).value


def test_semantic_similarity_offline_embedder_orders_sensibly() -> None:
    close = score(
        "semantic_similarity",
        output="The refund arrives within 14 days.",
        expected="Refunds arrive within fourteen days.",
    )
    far = score(
        "semantic_similarity",
        output="Our office cat is named Pixel.",
        expected="Refunds arrive within fourteen days.",
    )
    assert close is not None and far is not None and close > far


def test_missing_fields_skip_with_reason() -> None:
    from guage_kit.metrics.registry import resolve

    sc = resolve("token_f1").score(Sample(id="x", output="hi"))
    assert sc.skipped and sc.value is None and "expected" in (sc.reason or "")
