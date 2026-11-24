"""Retrieval, classification and calibration metrics against scikit-learn and hand-computed values."""

from __future__ import annotations

import math
import random

import pytest
from sklearn import metrics as skm

from guage_kit.core.sample import Sample
from tests.conftest import corpus, score


def test_retrieval_hand_cases() -> None:
    f = {"retrieved_ids": ["a", "x", "b", "y"], "relevant_ids": ["a", "b", "c"]}
    assert score("precision@2", **f) == 0.5
    assert score("recall@3", **f) == pytest.approx(2 / 3)
    assert score("hit_rate@1", **f) == 1.0
    assert score("mrr", retrieved_ids=["x", "y", "a"], relevant_ids=["a"]) == pytest.approx(1 / 3)
    assert score("average_precision", **f) == pytest.approx((1 / 1 + 2 / 3) / 3)
    assert score("r_precision", **f) == pytest.approx(2 / 3)
    assert score("mrr", retrieved_ids=["x"], relevant_ids=["a"]) == 0.0


def test_ndcg_matches_sklearn_graded() -> None:
    rng = random.Random(1)
    for _ in range(20):
        docs = [f"d{i}" for i in range(8)]
        gains = {d: float(rng.choice([0, 0, 1, 2, 3])) for d in docs}
        if not any(gains.values()):
            gains["d0"] = 1.0
        ranking = docs[:]
        rng.shuffle(ranking)
        k = rng.choice([3, 5, 8])
        ours = score(f"ndcg@{k}", retrieved_ids=ranking, relevance=gains)
        y_true = [[gains[d] for d in ranking]]
        y_score = [[len(ranking) - i for i in range(len(ranking))]]
        assert ours == pytest.approx(skm.ndcg_score(y_true, y_score, k=k), abs=1e-9)


def _cls(n: int = 80, seed: int = 0) -> tuple[list[Sample], list[str], list[str]]:
    rng = random.Random(seed)
    labels = ["a", "b", "c", "d"]
    gold, pred, samples = [], [], []
    for i in range(n):
        g = rng.choices(labels, weights=[5, 3, 2, 1])[0]
        p = g if rng.random() < 0.7 else rng.choice(labels)
        conf = rng.uniform(0.5, 1.0) if p == g else rng.uniform(0.3, 0.9)
        gold.append(g)
        pred.append(p)
        samples.append(Sample(id=str(i), expected=g, label=p, confidence=conf))
    return samples, gold, pred


@pytest.mark.parametrize("average", ["macro", "micro", "weighted"])
def test_f1_precision_recall_match_sklearn(average: str) -> None:
    samples, gold, pred = _cls()
    labels = sorted(set(gold))
    assert corpus("f1", samples, average=average).value == pytest.approx(
        skm.f1_score(
            gold,
            pred,
            average=average,
            labels=labels if average == "macro" else None,
            zero_division=0,
        )
    )
    assert corpus("precision_score", samples, average=average).value == pytest.approx(
        skm.precision_score(
            gold,
            pred,
            average=average,
            labels=labels if average == "macro" else None,
            zero_division=0,
        )
    )
    assert corpus("recall_score", samples, average=average).value == pytest.approx(
        skm.recall_score(
            gold,
            pred,
            average=average,
            labels=labels if average == "macro" else None,
            zero_division=0,
        )
    )


def test_agreement_metrics_match_sklearn() -> None:
    samples, gold, pred = _cls(seed=3)
    assert corpus("accuracy", samples).value == pytest.approx(skm.accuracy_score(gold, pred))
    assert corpus("cohen_kappa", samples).value == pytest.approx(skm.cohen_kappa_score(gold, pred))
    assert corpus("mcc", samples).value == pytest.approx(skm.matthews_corrcoef(gold, pred))
    assert corpus("balanced_accuracy", samples).value == pytest.approx(
        skm.balanced_accuracy_score(gold, pred)
    )
    out = corpus("accuracy", samples)
    assert sum(map(sum, out.details["confusion_matrix"])) == len(samples)


def test_binary_f1() -> None:
    s = [
        Sample(id=str(i), expected=g, label=p)
        for i, (g, p) in enumerate([("1", "1"), ("1", "0"), ("0", "0"), ("0", "1"), ("1", "1")])
    ]
    assert corpus("f1", s, average="binary", positive="1").value == pytest.approx(
        skm.f1_score([1, 1, 0, 0, 1], [1, 0, 0, 1, 1])
    )


def test_ece_hand_computed() -> None:
    # two bins: confidences 0.9 (2 right, 1 wrong) and 0.6 (1 right, 1 wrong)
    s = [
        Sample(id="1", expected="a", label="a", confidence=0.9),
        Sample(id="2", expected="a", label="a", confidence=0.9),
        Sample(id="3", expected="a", label="b", confidence=0.9),
        Sample(id="4", expected="a", label="a", confidence=0.6),
        Sample(id="5", expected="a", label="b", confidence=0.6),
    ]
    expected = 3 / 5 * abs(2 / 3 - 0.9) + 2 / 5 * abs(0.5 - 0.6)
    out = corpus("ece", s)
    assert out.value == pytest.approx(expected)
    assert len(out.details["reliability"]) == 2
    assert corpus("mce", s).value == pytest.approx(abs(2 / 3 - 0.9))


def test_brier_multiclass_and_auroc() -> None:
    assert score("brier", expected="a", probabilities={"a": 0.7, "b": 0.3}) == pytest.approx(
        0.09 + 0.09
    )
    samples, gold, pred = _cls(seed=5)
    correct = [1 if g == p else 0 for g, p in zip(gold, pred, strict=True)]
    conf = [s.confidence for s in samples]
    assert corpus("selective_auroc", samples).value == pytest.approx(
        skm.roc_auc_score(correct, conf)
    )


def test_predicted_label_from_probabilities() -> None:
    s = Sample(id="x", expected="b", probabilities={"a": 0.2, "b": 0.8})
    assert s.predicted_label == "b"
    assert score("label_match", expected="b", probabilities={"a": 0.2, "b": 0.8}) == 1.0


def test_sts_matches_scipy() -> None:
    from scipy import stats as sps

    rng = random.Random(0)
    samples = []
    gold, pred = [], []
    for i in range(30):
        a = [rng.gauss(0, 1) for _ in range(8)]
        b = [x + rng.gauss(0, 0.8) for x in a]
        g = rng.uniform(0, 5)
        samples.append(Sample(id=str(i), embeddings={"a": a, "b": b}, expected=g))
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        pred.append(dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))))
        gold.append(g)
    assert corpus("sts_spearman", samples).value == pytest.approx(
        sps.spearmanr(pred, gold).statistic
    )
    assert corpus("sts_pearson", samples).value == pytest.approx(sps.pearsonr(pred, gold).statistic)
    assert corpus("alignment", samples).value > 0
    assert corpus("uniformity", samples).value < 0
