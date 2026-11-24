---
title: Classification and calibration
description: Accuracy, F1 averages, agreement beyond chance, confusion matrices, and whether a model's confidence can be trusted.
---

# Classification and calibration

Use these metrics when the system picks a label: intent routing, moderation, extraction of a category, a yes/no
check.

## Data

- `expected`: the gold label.
- the prediction: `label`; otherwise the label with the highest `probabilities`; otherwise a short `output`.
- for calibration: `confidence`, or the top value of `probabilities`.

Labels are compared after trimming whitespace and, by default, ignoring case.

```python
import guage_kit as gk

data = [gk.Sample(id=str(i), input=t, expected=g, label=p, probabilities=pr) for i, (t, g, p, pr) in enumerate([
    ("I was charged twice", "billing", "billing", {"billing": 0.9, "bug": 0.1}),
    ("App crashes on PDF", "bug", "bug", {"billing": 0.2, "bug": 0.8}),
    ("Refund please", "billing", "bug", {"billing": 0.4, "bug": 0.6}),
    ("Sync stuck", "bug", "bug", {"billing": 0.3, "bug": 0.7}),
])]
run = gk.evaluate(data, ["accuracy", "f1", "cohen_kappa", "ece", "brier"])
print({k: round(v.value, 3) for k, v in run.summaries.items()})
print(run.summaries["accuracy"].details["confusion_matrix"], run.summaries["accuracy"].details["labels"])
```

```text
{'brier': 0.25, 'accuracy': 0.75, 'f1': 0.733, 'cohen_kappa': 0.5, 'ece': 0.3}
[[1, 1], [0, 2]] ['billing', 'bug']
```

(Sample-level metrics such as `brier` are listed before corpus metrics in the summaries.)

## Metrics

| Metric | Level | Notes |
| --- | --- | --- |
| `label_match` | sample | 1 when the prediction equals the gold label |
| `accuracy` | corpus | details carry the confusion matrix (rows gold, columns predicted) and label order |
| `f1`, `precision_score`, `recall_score` | corpus | `average`: `macro` (default; over gold labels), `micro`, `weighted`, or `binary` with `positive`; details carry per-label precision, recall, F1 and support |
| `balanced_accuracy` | corpus | mean recall over gold labels; robust to imbalance |
| `cohen_kappa` | corpus | agreement beyond chance (−1 to 1) |
| `mcc` | corpus | Matthews correlation, multi-class form (−1 to 1) |

These are tested against scikit-learn's implementations.

## Calibration

A calibrated model that says "90% sure" is right about 90% of the time. That matters whenever confidence drives a
decision, such as routing low-confidence cases to a person.

| Metric | Level | Notes |
| --- | --- | --- |
| `ece` | corpus | expected calibration error over `n_bins` (default 10) equal-width bins; details carry the reliability diagram (per bin: confidence, accuracy, count) |
| `mce` | corpus | the worst bin's gap |
| `brier` | sample | squared error of the probabilities against the one-hot gold label (with only `confidence`: of the confidence against correctness) |
| `selective_auroc` | corpus | AUROC of confidence as a predictor of being right. Does the model know when it is wrong? 0.5 is no better than chance |

The report draws the reliability diagram and the confusion matrix on the metric's detail panel.

## Tips

- Prefer `f1` (macro) or `balanced_accuracy` over `accuracy` when classes are imbalanced.
- Slice by gold label (`tags: [<label>]` and `slices: [tags]`) to see which class drags the average down.
- ECE with few samples per bin is noisy. Look at its confidence interval, or lower `n_bins`.
