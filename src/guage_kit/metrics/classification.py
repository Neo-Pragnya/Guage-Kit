"""Classification and calibration metrics.

The gold label is ``expected``; the prediction is ``label``, else the arg-max of ``probabilities``, else a short
``output``. Calibration uses ``confidence`` (or the top probability) against whether the prediction was right.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from guage_kit.core.sample import Sample
from guage_kit.metrics.registry import CorpusOutput, corpus_metric, metric

_F = "classification"
_C = "calibration"
_REQ = ("label", "expected")


def _pairs(samples: list[Sample], case_sensitive: bool = False) -> list[tuple[str, str]]:
    def norm(x: str) -> str:
        x = x.strip()
        return x if case_sensitive else x.lower()

    out = []
    for s in samples:
        pred = s.predicted_label
        if pred is None or not s.expected_texts:
            continue
        out.append((norm(s.expected_texts[0]), norm(pred)))
    return out


def confusion(pairs: list[tuple[str, str]]) -> tuple[list[str], list[list[int]]]:
    labels = sorted({g for g, _ in pairs} | {p for _, p in pairs})
    index = {lab: i for i, lab in enumerate(labels)}
    matrix = [[0] * len(labels) for _ in labels]
    for g, p in pairs:
        matrix[index[g]][index[p]] += 1
    return labels, matrix


@metric("label_match", family=_F, requires=_REQ)
def label_match(sample: Sample, *, case_sensitive: bool = False) -> float:
    """1 when the predicted label equals the gold label (the per-sample view of accuracy)."""
    ((g, p),) = _pairs([sample], case_sensitive)
    return float(g == p)


@corpus_metric("accuracy", family=_F, requires=_REQ)
def accuracy(samples: list[Sample], *, case_sensitive: bool = False) -> CorpusOutput:
    """Share of correct predictions, with the confusion matrix in the details."""
    pairs = _pairs(samples, case_sensitive)
    labels, matrix = confusion(pairs)
    per = {s.id: float(g == p) for s, (g, p) in zip(samples, pairs, strict=False)}
    return CorpusOutput(
        sum(g == p for g, p in pairs) / len(pairs) if pairs else None,
        {"labels": labels, "confusion_matrix": matrix},
        per,
    )


def _prf(pairs: list[tuple[str, str]]) -> dict[str, dict[str, float]]:
    labels = sorted({g for g, _ in pairs} | {p for _, p in pairs})
    out: dict[str, dict[str, float]] = {}
    for lab in labels:
        tp = sum(1 for g, p in pairs if g == lab and p == lab)
        fp = sum(1 for g, p in pairs if g != lab and p == lab)
        fn = sum(1 for g, p in pairs if g == lab and p != lab)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f = 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)
        out[lab] = {
            "precision": prec,
            "recall": rec,
            "f1": f,
            "support": tp + fn,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }
    return out


def _averaged(
    samples: list[Sample], key: str, average: str, positive: str
) -> tuple[float | None, dict[str, Any]]:
    pairs = _pairs(samples)
    if not pairs:
        return None, {}
    per = _prf(pairs)
    details: dict[str, Any] = {
        "per_label": {k: {m: round(v, 4) for m, v in d.items()} for k, d in per.items()}
    }
    if average == "binary":
        p = positive.lower()
        return (per.get(p, {}).get(key, 0.0)), details
    if average == "micro":
        tp = sum(d["tp"] for d in per.values())
        fp = sum(d["fp"] for d in per.values())
        fn = sum(d["fn"] for d in per.values())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        vals = {
            "precision": prec,
            "recall": rec,
            "f1": 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec),
        }
        return vals[key], details
    gold_labels = {g for g, _ in pairs}
    considered = {k: d for k, d in per.items() if k in gold_labels}
    if average == "weighted":
        total = sum(d["support"] for d in considered.values())
        return sum(
            d[key] * d["support"] for d in considered.values()
        ) / total if total else 0.0, details
    return sum(d[key] for d in considered.values()) / len(considered), details  # macro


@corpus_metric("f1", family=_F, requires=_REQ)
def f1_score(
    samples: list[Sample], *, average: str = "macro", positive: str = "1"
) -> tuple[float | None, dict[str, Any]]:
    """F1 averaged ``macro`` (default), ``micro``, ``weighted`` or ``binary`` (with ``positive``)."""
    return _averaged(samples, "f1", average, positive)


@corpus_metric("precision_score", family=_F, requires=_REQ)
def precision_score(
    samples: list[Sample], *, average: str = "macro", positive: str = "1"
) -> tuple[float | None, dict[str, Any]]:
    """Classification precision, averaged like ``f1``."""
    return _averaged(samples, "precision", average, positive)


@corpus_metric("recall_score", family=_F, requires=_REQ)
def recall_score(
    samples: list[Sample], *, average: str = "macro", positive: str = "1"
) -> tuple[float | None, dict[str, Any]]:
    """Classification recall, averaged like ``f1``."""
    return _averaged(samples, "recall", average, positive)


@corpus_metric("balanced_accuracy", family=_F, requires=_REQ)
def balanced_accuracy(samples: list[Sample]) -> float | None:
    """Mean recall over the gold labels (robust to class imbalance)."""
    return _averaged(samples, "recall", "macro", "")[0]


@corpus_metric(
    "cohen_kappa", family=_F, requires=_REQ, value_range=(-1.0, 1.0), reference="Cohen (1960)"
)
def cohen_kappa(samples: list[Sample]) -> float | None:
    """Agreement between prediction and gold beyond chance (also used for judge-vs-human agreement)."""
    pairs = _pairs(samples)
    n = len(pairs)
    if not n:
        return None
    po = sum(g == p for g, p in pairs) / n
    gc, pc = Counter(g for g, _ in pairs), Counter(p for _, p in pairs)
    pe = sum(gc[k] * pc[k] for k in gc) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


@corpus_metric(
    "mcc",
    family=_F,
    requires=_REQ,
    value_range=(-1.0, 1.0),
    reference="Gorodkin (2004), multiclass MCC",
)
def mcc(samples: list[Sample]) -> float | None:
    """Matthews correlation coefficient (multi-class form)."""
    pairs = _pairs(samples)
    if not pairs:
        return None
    labels, C = confusion(pairs)
    t = [sum(row) for row in C]
    p = [sum(C[i][j] for i in range(len(labels))) for j in range(len(labels))]
    c = sum(C[i][i] for i in range(len(labels)))
    s = len(pairs)
    num = c * s - sum(pk * tk for pk, tk in zip(p, t, strict=True))
    den = math.sqrt((s * s - sum(x * x for x in p)) * (s * s - sum(x * x for x in t)))
    return num / den if den else 0.0


# ── calibration ──────────────────────────────────────────────────────────────────────────────────────────────────
def _conf_correct(samples: list[Sample]) -> list[tuple[float, float]]:
    out = []
    for s in samples:
        conf = s.confidence
        if conf is None and s.probabilities:
            conf = max(s.probabilities.values())
        pred = s.predicted_label
        if conf is None or pred is None or not s.expected_texts:
            continue
        correct = float(pred.strip().lower() == s.expected_texts[0].strip().lower())
        out.append((min(max(float(conf), 0.0), 1.0), correct))
    return out


def reliability(pairs: list[tuple[float, float]], n_bins: int) -> list[dict[str, float]]:
    bins: list[dict[str, float]] = []
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        members = [(c, y) for c, y in pairs if (lo < c <= hi) or (b == 0 and c == 0)]
        if members:
            bins.append(
                {
                    "lo": lo,
                    "hi": hi,
                    "count": len(members),
                    "confidence": sum(c for c, _ in members) / len(members),
                    "accuracy": sum(y for _, y in members) / len(members),
                }
            )
    return bins


_CAL_REQ = ("label", "expected")
_CAL_ANY = ("confidence", "probabilities")


@corpus_metric(
    "ece",
    family=_C,
    requires=_CAL_REQ,
    requires_any=_CAL_ANY,
    higher_is_better=False,
    reference="Naeini et al. (2015); Guo et al. (2017)",
)
def ece(samples: list[Sample], *, n_bins: int = 10) -> tuple[float | None, dict[str, Any]]:
    """Expected calibration error: weighted gap between confidence and accuracy over equal-width bins."""
    pairs = _conf_correct(samples)
    if not pairs:
        return None, {}
    bins = reliability(pairs, n_bins)
    value = sum(b["count"] / len(pairs) * abs(b["accuracy"] - b["confidence"]) for b in bins)
    return value, {"reliability": bins}


@corpus_metric("mce", family=_C, requires=_CAL_REQ, requires_any=_CAL_ANY, higher_is_better=False)
def mce(samples: list[Sample], *, n_bins: int = 10) -> float | None:
    """Maximum calibration error: the worst bin's confidence–accuracy gap."""
    pairs = _conf_correct(samples)
    bins = reliability(pairs, n_bins)
    return max((abs(b["accuracy"] - b["confidence"]) for b in bins), default=None)


@metric(
    "brier",
    family=_C,
    requires=("expected",),
    requires_any=_CAL_ANY,
    higher_is_better=False,
    value_range=(0.0, 2.0),  # the multi-class form reaches 2
    reference="Brier (1950)",
)
def brier(sample: Sample) -> float | None:
    """Brier score: squared error of the probabilities against the one-hot gold label (0 is perfect)."""
    gold = sample.expected_texts[0].strip().lower()
    if sample.probabilities:
        probs = {k.strip().lower(): v for k, v in sample.probabilities.items()}
        labels = set(probs) | {gold}
        return sum((probs.get(lab, 0.0) - (1.0 if lab == gold else 0.0)) ** 2 for lab in labels)
    pred = sample.predicted_label
    if pred is None or sample.confidence is None:
        return None
    correct = float(pred.strip().lower() == gold)
    return (sample.confidence - correct) ** 2


@corpus_metric("selective_auroc", family=_C, requires=_CAL_REQ, requires_any=_CAL_ANY)
def selective_auroc(samples: list[Sample]) -> float | None:
    """AUROC of confidence as a predictor of correctness: does the model know when it is wrong?"""
    pairs = _conf_correct(samples)
    pos = [c for c, y in pairs if y == 1]
    neg = [c for c, y in pairs if y == 0]
    if not pos or not neg:
        return None
    wins = sum((1.0 if p > n else 0.5 if p == n else 0.0) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))
