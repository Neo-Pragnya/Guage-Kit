---
title: Calibration metrics
description: "Whether confidence matches accuracy: ECE, MCE, Brier score, selective AUROC."
---

# Calibration metrics

> [!NOTE]
> Generated from the metric registry and the metric cards (`guage_kit/metrics/cards/`). Every example
> on this page is run by the test suite, so the numbers are what the metric really returns.

Whether confidence matches accuracy: ECE, MCE, Brier score, selective AUROC.

| metric | in one line |
| --- | --- |
| [`brier`](#brier) | The squared error between the predicted probabilities and the true label, per sample (0 is perfect). |
| [`ece`](#ece) | The average gap between how confident the model says it is and how often it is right, over confidence bins. |
| [`mce`](#mce) | The largest gap between confidence and accuracy in any confidence bin, the worst-case calibration error. |
| [`selective_auroc`](#selective_auroc) | How well the model's confidence separates its correct answers from its wrong ones (0.5 is chance, 1 is perfect). |

## brier

*The squared error between the predicted probabilities and the true label, per sample (0 is perfect).*

**Level:** sample · **Range:** 0 to 2, lower is better · **Needs:** `expected`, `confidence` or `probabilities` · **Deterministic:** yes

**What it measures**

The accuracy of probabilistic predictions: both whether the right class gets high probability and whether the wrong classes get low probability. It rewards confident correct answers, and penalises confident wrong ones heavily.

**How it is computed**

1. Read the gold label from the first `expected` label (trimmed, lowercased).
2. If `probabilities` is present: lowercase and trim its keys, then sum, over every label in the
   probabilities plus the gold label, the squared difference between the predicted probability (0 if missing)
   and the one-hot target (1 for the gold label, 0 otherwise). This is the original multi-class Brier score.
3. Otherwise, if `confidence` and a predicted label are present: return (confidence − correct)², where correct
   is 1 when the predicted label equals the gold label. This is the binary Brier score of the confidence as a
   probability of being right.
4. A sample with neither is skipped. The run summary is the mean over samples.

```text
with probabilities:  BS = Σ_k ( p_k − [k == gold] )²             range 0..2
with confidence:     BS = ( conf − [pred == gold] )²             range 0..1
run value = mean of BS over samples
```

**Inputs:** `expected` (gold label) and either `probabilities` (a dict of label to probability) or `confidence` together with a predicted label (`label` or short `output`).

**How to read it**

Lower is better; 0 means all probability on the right label. In the multi-class form the worst case is 2 (all probability on one wrong label); in the confidence form it is 1. Always predicting the uniform distribution over K classes scores 1 − 1/K, a useful baseline. The Brier score is a strictly proper scoring rule: a model minimises it in expectation only by reporting its true beliefs.

**Use it when**

- You have full class probabilities and want one score that combines calibration and sharpness.
- Comparing probability outputs from different models or calibration methods.

**Pitfalls**

- The two input forms give different numbers on different scales; do not mix samples with `probabilities` and samples with only `confidence` in one comparison.
- The multi-class form ranges 0–2 and the binary form 0–1, so values from the two forms are not comparable; keep a dataset to one form.
- Dominated by the common classes on imbalanced data; a model can score well while being poor on rare classes.
- Probabilities that do not sum to 1 are not renormalised, and keys that collide after lowercasing overwrite each other.

**Example** (checked by the test suite against the real metric)

```jsonl
{"expected": "billing", "probabilities": {"billing": 0.7, "bug": 0.2, "refund": 0.1}}
```

Result: **0.14**. (0.7 − 1)² + 0.2² + 0.1² = 0.09 + 0.04 + 0.01.

**Related:** [`ece`](#ece), [`mce`](#mce), [`selective_auroc`](#selective_auroc)

**References**

- Brier, G. W. (1950). Verification of forecasts expressed in terms of probability. Monthly Weather Review, 78(1), pp. 1–3. <https://doi.org/10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2>
- Gneiting, T., and Raftery, A. E. (2007). Strictly Proper Scoring Rules, Prediction, and Estimation. Journal of the American Statistical Association, 102(477), pp. 359–378. <https://doi.org/10.1198/016214506000001437>

## ece

*The average gap between how confident the model says it is and how often it is right, over confidence bins.*

**Level:** corpus · **Range:** 0 to 1, lower is better · **Needs:** `label`, `expected`, `confidence` or `probabilities` · **Deterministic:** yes

**What it measures**

Calibration of the model's confidence in its own predicted label. It answers "when the model says 80%, is it right about 80% of the time?" A well-calibrated model lets you use confidence for decisions such as sending low-confidence cases to a person.

**How it is computed**

1. For each sample, take the confidence: `confidence` if set, otherwise the largest value in `probabilities`.
   Clip it to [0, 1].
2. Take the predicted label (`label`, else arg-max of `probabilities`, else a short `output`) and mark the sample
   correct (1) or wrong (0) by comparing it with the first `expected` label, trimmed and case-insensitive.
3. Split [0, 1] into `n_bins` equal-width bins (lo, hi]; a confidence of exactly 0 goes into the first bin.
4. In each non-empty bin compute the mean confidence and the accuracy (share correct).
5. ECE is the sample-weighted mean of |accuracy − confidence| over bins. The per-bin numbers (lo, hi, count,
   confidence, accuracy) are returned in the details as `reliability`, the data of a reliability diagram.
This is the top-label (confidence) ECE of Guo et al. (2017), not a class-wise or adaptive-binning variant.

```text
B_m  = { i : (m−1)/M < conf_i ≤ m/M }            M = n_bins
acc(B_m)  = (1/|B_m|) Σ_{i∈B_m} [ pred_i == gold_i ]
conf(B_m) = (1/|B_m|) Σ_{i∈B_m} conf_i
ECE = Σ_m (|B_m| / N) · | acc(B_m) − conf(B_m) |
```

**Inputs:** `expected` (gold label), a prediction (`label`, `probabilities` or short `output`) and a confidence (`confidence`, or the top value of `probabilities`).

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `n_bins` | `10` | Number of equal-width confidence bins (default 10). Fewer bins give steadier estimates on small datasets; more bins show finer detail but each bin holds fewer samples. |

**How to read it**

0 to 1, lower is better; 0 means confidence matches accuracy in every bin. Values under about 0.05 are usually considered well calibrated. Look at the reliability bins: accuracy below confidence means over-confidence (the common case for modern networks and verbalised LLM confidences), above means under-confidence.

**Use it when**

- Model confidence drives a decision (thresholding, abstention, routing to a human).
- Comparing calibration before and after temperature scaling or prompt changes.

**Pitfalls**

- Binning-sensitive. The value changes with `n_bins` (the example gives 0.219 with 10 bins and 0.189 with 5), and with few samples per bin it is noisy and biased upward. Report `n_bins` and the confidence interval.
- A model can have low ECE and still be useless, e.g. always predicting the majority class with confidence equal to its frequency. Pair it with accuracy and `selective_auroc`.
- It only looks at the top label's confidence; it says nothing about the calibration of the other class probabilities (use `brier` for that).
- Self-reported (verbalised) confidences cluster on round numbers such as 0.9 and 0.95, which leaves most bins empty.

**Example** (checked by the test suite against the real metric)

```jsonl
{"expected": "a", "label": "a", "confidence": 0.95}
{"expected": "a", "label": "a", "confidence": 0.92}
{"expected": "a", "label": "b", "confidence": 0.91}
{"expected": "a", "label": "a", "confidence": 0.85}
{"expected": "a", "label": "a", "confidence": 0.75}
{"expected": "a", "label": "b", "confidence": 0.72}
{"expected": "a", "label": "b", "confidence": 0.65}
{"expected": "a", "label": "a", "confidence": 0.62}
{"expected": "a", "label": "b", "confidence": 0.55}
{"expected": "a", "label": "a", "confidence": 0.97}
```

Result: **0.219**. Accuracy is 0.6 against a mean confidence of 0.789, so the model is over-confident. With n_bins=5 the same data gives 0.189.

**Related:** [`mce`](#mce), [`brier`](#brier), [`selective_auroc`](#selective_auroc), [`accuracy`](classification.md#accuracy)

**References**

- Naeini, M. P., Cooper, G. F., and Hauskrecht, M. (2015). Obtaining Well Calibrated Probabilities Using Bayesian Binning. Proceedings of the AAAI Conference on Artificial Intelligence, 29, pp. 2901–2907. <https://pmc.ncbi.nlm.nih.gov/articles/PMC4410090/>
- Guo, C., Pleiss, G., Sun, Y., and Weinberger, K. Q. (2017). On Calibration of Modern Neural Networks. Proceedings of the 34th International Conference on Machine Learning (ICML), PMLR 70, pp. 1321–1330. <https://arxiv.org/abs/1706.04599>
- Nixon, J., Dusenberry, M., Zhang, L., Jerfel, G., and Tran, D. (2019). Measuring Calibration in Deep Learning. CVPR Workshops 2019. <https://arxiv.org/abs/1904.01685>

## mce

*The largest gap between confidence and accuracy in any confidence bin, the worst-case calibration error.*

**Level:** corpus · **Range:** 0 to 1, lower is better · **Needs:** `label`, `expected`, `confidence` or `probabilities` · **Deterministic:** yes

**What it measures**

How badly calibrated the model is in its worst confidence range. It answers "is there a confidence level at which the model's stated certainty is far from the truth?", which matters when decisions at one specific confidence level are high-stakes.

**How it is computed**

1. Build the same (confidence, correct) pairs and equal-width bins as `ece`: confidence is `confidence` or the
   top value of `probabilities`, clipped to [0, 1]; correctness compares the predicted label with the first
   `expected` label, trimmed and case-insensitive.
2. For each non-empty bin compute |accuracy − mean confidence|.
3. Return the largest of these gaps. Bins are not weighted by size, so a bin holding a single sample counts
   as much as one holding hundreds.

```text
MCE = max_{m : |B_m| > 0} | acc(B_m) − conf(B_m) |
```

**Inputs:** `expected` (gold label), a prediction (`label`, `probabilities` or short `output`) and a confidence (`confidence`, or the top value of `probabilities`).

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `n_bins` | `10` | Number of equal-width confidence bins (default 10). With fewer bins each gap is an average over more samples and the maximum is less driven by outliers. |

**How to read it**

0 to 1, lower is better. Always read it with the reliability bins in `ece`'s details: an MCE of 0.5 from a bin of one sample means little, from a bin of 200 samples it is a real problem.

**Use it when**

- Safety-critical thresholds, where a badly calibrated region matters even if it is rare.
- As a complement to `ece`, which can average a bad region away.

**Pitfalls**

- Extremely sensitive to sparsely populated bins. In the example the maximum comes from a bin holding one wrong prediction at confidence 0.55.
- Grows with `n_bins` and shrinks with dataset size for the same model, so values from different setups are not comparable.
- Says nothing about how many samples are affected.

**Example** (checked by the test suite against the real metric)

```jsonl
{"expected": "a", "label": "a", "confidence": 0.95}
{"expected": "a", "label": "a", "confidence": 0.92}
{"expected": "a", "label": "b", "confidence": 0.91}
{"expected": "a", "label": "a", "confidence": 0.85}
{"expected": "a", "label": "a", "confidence": 0.75}
{"expected": "a", "label": "b", "confidence": 0.72}
{"expected": "a", "label": "b", "confidence": 0.65}
{"expected": "a", "label": "a", "confidence": 0.62}
{"expected": "a", "label": "b", "confidence": 0.55}
{"expected": "a", "label": "a", "confidence": 0.97}
```

Result: **0.55**. The worst bin, (0.5, 0.6], holds one wrong prediction made at confidence 0.55.

**Related:** [`ece`](#ece), [`brier`](#brier), [`selective_auroc`](#selective_auroc)

**References**

- Naeini, M. P., Cooper, G. F., and Hauskrecht, M. (2015). Obtaining Well Calibrated Probabilities Using Bayesian Binning. Proceedings of the AAAI Conference on Artificial Intelligence, 29, pp. 2901–2907. <https://pmc.ncbi.nlm.nih.gov/articles/PMC4410090/>
- Guo, C., Pleiss, G., Sun, Y., and Weinberger, K. Q. (2017). On Calibration of Modern Neural Networks. Proceedings of the 34th International Conference on Machine Learning (ICML), PMLR 70, pp. 1321–1330. <https://arxiv.org/abs/1706.04599>

## selective_auroc

*How well the model's confidence separates its correct answers from its wrong ones (0.5 is chance, 1 is perfect).*

**Level:** corpus · **Range:** 0 to 1, higher is better · **Needs:** `label`, `expected`, `confidence` or `probabilities` · **Deterministic:** yes

**What it measures**

Whether the model knows when it is wrong. It answers "if I pick one correct and one wrong prediction at random, how often does the correct one have higher confidence?" This is what matters for selective prediction: abstaining on, or escalating, the least confident cases.

**How it is computed**

1. Build (confidence, correct) pairs as in `ece`: confidence is `confidence` or the top value of
   `probabilities`, clipped to [0, 1]; correct compares the predicted label with the first `expected` label,
   trimmed and case-insensitive.
2. Split into correct and wrong predictions. If either group is empty, the value is undefined (no value).
3. Compare every correct prediction with every wrong one: a win if the correct one is more confident, half a
   win on a tie. AUROC is the share of wins (the Mann–Whitney form of the area under the ROC curve).
The positive class is "prediction is correct" and the score being ranked is the confidence.

```text
AUROC = (1 / (|P|·|W|)) Σ_{i∈P} Σ_{j∈W} ( [c_i > c_j] + 0.5·[c_i = c_j] )
P = correct predictions, W = wrong predictions, c = confidence
```

**Inputs:** `expected` (gold label), a prediction (`label`, `probabilities` or short `output`) and a confidence (`confidence`, or the top value of `probabilities`).

**How to read it**

0 to 1, higher is better. 0.5 means confidence carries no information about correctness; below 0.5 means the model is more confident when it is wrong. Unlike `ece`, it ignores the absolute confidence values and only looks at their order, so a badly calibrated model can still have a high selective AUROC (and recalibration with a monotone map does not change it).

**Use it when**

- Deciding whether confidence can be used to abstain, defer to a human, or trigger a second check.
- Comparing confidence signals (verbalised confidence, token log-probabilities, self-consistency) for the same model.

**Pitfalls**

- Undefined when the model is always right or always wrong on the dataset.
- {'Order-only': 'says nothing about whether 0.9 really means 90%; read it with `ece`.'}
- Comparing two models with different accuracy is subtle, since each AUROC is computed over its own set of errors.
- Verbalised confidences with many ties (everything 0.9) push the value towards 0.5.

**Example** (checked by the test suite against the real metric)

```jsonl
{"expected": "a", "label": "a", "confidence": 0.95}
{"expected": "a", "label": "a", "confidence": 0.92}
{"expected": "a", "label": "b", "confidence": 0.91}
{"expected": "a", "label": "a", "confidence": 0.85}
{"expected": "a", "label": "a", "confidence": 0.75}
{"expected": "a", "label": "b", "confidence": 0.72}
{"expected": "a", "label": "b", "confidence": 0.65}
{"expected": "a", "label": "a", "confidence": 0.62}
{"expected": "a", "label": "b", "confidence": 0.55}
{"expected": "a", "label": "a", "confidence": 0.97}
```

Result: **0.7917**. Same as sklearn.metrics.roc_auc_score(correct, confidence). The same data has ECE 0.219, so confidence ranks well but is over-stated.

**Related:** [`ece`](#ece), [`mce`](#mce), [`brier`](#brier), [`accuracy`](classification.md#accuracy)

**References**

- Geifman, Y., and El-Yaniv, R. (2017). Selective Classification for Deep Neural Networks. Advances in Neural Information Processing Systems 30 (NeurIPS 2017). <https://arxiv.org/abs/1705.08500>
- Hendrycks, D., and Gimpel, K. (2017). A Baseline for Detecting Misclassified and Out-of-Distribution Examples in Neural Networks. International Conference on Learning Representations (ICLR 2017). <https://arxiv.org/abs/1610.02136>
- Fawcett, T. (2006). An introduction to ROC analysis. Pattern Recognition Letters, 27(8), pp. 861–874. <https://doi.org/10.1016/j.patrec.2005.10.010>
