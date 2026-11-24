---
title: Classification metrics
description: "Labels against gold labels: accuracy, F1, kappa, MCC."
---

# Classification metrics

> [!NOTE]
> Generated from the metric registry and the metric cards (`guage_kit/metrics/cards/`). Every example
> on this page is run by the test suite, so the numbers are what the metric really returns.

Labels against gold labels: accuracy, F1, kappa, MCC.

| metric | in one line |
| --- | --- |
| [`accuracy`](#accuracy) | The share of samples whose predicted label equals the gold label, with the confusion matrix in the details. |
| [`balanced_accuracy`](#balanced_accuracy) | The average of the per-class recall, so every gold class counts equally however rare it is. |
| [`cohen_kappa`](#cohen_kappa) | Agreement between predicted and gold labels after removing the agreement expected by chance. |
| [`f1`](#f1) | The harmonic mean of precision and recall per label, averaged over labels (macro by default). |
| [`label_match`](#label_match) | 1 when the predicted label equals the gold label for this sample, else 0. |
| [`mcc`](#mcc) | The Matthews correlation coefficient between predicted and gold labels, in its multi-class form. |
| [`precision_score`](#precision_score) | Of the samples given a label, the share that truly have it, averaged over labels (macro by default). |
| [`recall_score`](#recall_score) | Of the samples that truly have a label, the share the model found, averaged over labels (macro by default). |

## accuracy

*The share of samples whose predicted label equals the gold label, with the confusion matrix in the details.*

**Level:** corpus · **Range:** 0 to 1, higher is better · **Needs:** `label`, `expected` · **Deterministic:** yes

**What it measures**

How often the classifier is right overall. It answers "out of every hundred inputs, how many get the correct label?" and treats every sample, and therefore every class in proportion to its frequency, equally.

**How it is computed**

1. For each sample, read the gold label (`expected`) and the prediction (`label`, else arg-max of
   `probabilities`, else a short `output`). Samples without both are dropped before scoring.
2. Normalise both by trimming whitespace and, unless `case_sensitive` is true, lowercasing.
3. Count the matches and divide by the number of scored samples.
4. Build the confusion matrix over the sorted union of gold and predicted labels (rows are gold, columns are
   predicted) and return it in the details as `confusion_matrix` with the label order in `labels`.

```text
accuracy = (1/N) Σ_i [ pred_i == gold_i ]
         = trace(C) / Σ C          (C = confusion matrix, rows gold, columns predicted)
```

**Inputs:** `expected` (gold label) and the prediction from `label`, the arg-max of `probabilities`, or a short `output`.

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `case_sensitive` | `False` | When true, labels that differ only in case are different classes (and get separate rows in the confusion matrix). Default false. |

**How to read it**

0 to 1, higher is better. Always compare it with the majority-class baseline (the share of the most common gold label): with 90% of samples in one class, 0.90 is what a model that always says that class gets. Read the confusion matrix in the details to see which classes are confused with which.

**Use it when**

- Classes are roughly balanced and every error costs the same.
- You want a single number that non-specialists understand, reported alongside a per-class view.

**Pitfalls**

- Misleading under class imbalance. A spam filter that never flags spam is 95% accurate on a 5% spam set; use `balanced_accuracy`, macro `f1` or `mcc`.
- Treats all errors alike; it cannot tell a harmless confusion from a costly one. Inspect the confusion matrix.
- Samples with no prediction are left out rather than counted wrong, so a model that often fails to answer can look better than it is. Check the `n` in the details against the dataset size.

**Example** (checked by the test suite against the real metric)

```jsonl
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "bug"}
{"expected": "bug", "label": "bug"}
{"expected": "bug", "label": "billing"}
{"expected": "refund", "label": "refund"}
{"expected": "refund", "label": "billing"}
{"expected": "refund", "label": "billing"}
```

Result: **0.6**. Same as sklearn.metrics.accuracy_score. Always answering "billing" would score 0.5 here; compare with balanced_accuracy (0.5444) on the same data.

**Related:** [`label_match`](#label_match), [`balanced_accuracy`](#balanced_accuracy), [`f1`](#f1), [`mcc`](#mcc), [`cohen_kappa`](#cohen_kappa)

**References**

- Sokolova, M., and Lapalme, G. (2009). A systematic analysis of performance measures for classification tasks. Information Processing & Management, 45(4), pp. 427–437. <https://doi.org/10.1016/j.ipm.2009.03.002>

## balanced_accuracy

*The average of the per-class recall, so every gold class counts equally however rare it is.*

**Level:** corpus · **Range:** 0 to 1, higher is better · **Needs:** `label`, `expected` · **Deterministic:** yes

**What it measures**

How well the classifier recognises each class, averaged over classes. It answers "if every class were equally common, how often would the model be right?" A model that always predicts the majority class scores 1/K with K gold classes, not the majority share.

**How it is computed**

1. Read and normalise gold and predicted labels as for `accuracy` (trimmed, case-insensitive).
2. For each label that appears in the gold labels, compute recall = TP / (TP + FN), the share of that class's
   samples predicted correctly.
3. Average those recalls with equal weight. Labels that occur only in predictions (never in gold) are not
   averaged over.

```text
recall_k          = TP_k / (TP_k + FN_k)
balanced_accuracy = (1/K) Σ_{k ∈ gold labels} recall_k        K = number of distinct gold labels
```

**Inputs:** `expected` (gold label) and the prediction from `label`, the arg-max of `probabilities`, or a short `output`.

**How to read it**

0 to 1, higher is better. Chance level for a classifier that ignores its input is 1/K (0.5 for binary). It equals `accuracy` when the classes are perfectly balanced, and is identical to macro-averaged `recall_score`. A large gap between accuracy and balanced accuracy means the model does well on common classes and poorly on rare ones.

**Use it when**

- Classes are imbalanced and missing a rare class matters as much as missing a common one.
- You want a figure whose chance level does not move with class frequencies.

**Pitfalls**

- Ignores precision. A model that over-predicts a rare class raises that class's recall at the cost of false positives elsewhere, which only partly shows up.
- A class with one or two gold samples moves the average by a large step; check the per-label details of `recall_score`.
- Classes the model predicts but that never occur in gold do not enter the average.

**Example** (checked by the test suite against the real metric)

```jsonl
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "bug"}
{"expected": "bug", "label": "bug"}
{"expected": "bug", "label": "billing"}
{"expected": "refund", "label": "refund"}
{"expected": "refund", "label": "billing"}
{"expected": "refund", "label": "billing"}
```

Result: **0.5444**. Recalls are billing 4/5, bug 1/2, refund 1/3; their mean is 0.5444. Same as sklearn.metrics.balanced_accuracy_score.

**Related:** [`accuracy`](#accuracy), [`recall_score`](#recall_score), [`f1`](#f1), [`mcc`](#mcc)

**References**

- Brodersen, K. H., Ong, C. S., Stephan, K. E., and Buhmann, J. M. (2010). The Balanced Accuracy and Its Posterior Distribution. Proceedings of the 20th International Conference on Pattern Recognition (ICPR), pp. 3121–3124. <https://doi.org/10.1109/ICPR.2010.764>

## cohen_kappa

*Agreement between predicted and gold labels after removing the agreement expected by chance.*

**Level:** corpus · **Range:** -1 to 1, higher is better · **Needs:** `label`, `expected` · **Deterministic:** yes

**What it measures**

Whether the predictions agree with the gold labels more than two raters who assigned labels at random with the same label frequencies would. It is also the standard measure of agreement between an LLM judge and human annotators.

**How it is computed**

1. Read and normalise gold and predicted labels (trimmed, case-insensitive).
2. Observed agreement p_o = share of samples where prediction equals gold (the accuracy).
3. Chance agreement p_e = Σ over labels of (share of gold with that label) × (share of predictions with that label).
4. kappa = (p_o − p_e) / (1 − p_e). When p_e = 1 (both sides use one and the same label throughout), the code
   returns 1.0 rather than an undefined value.
This is unweighted kappa: every disagreement counts the same, so it is for nominal labels, not ordinal scales.

```text
p_o   = (1/N) Σ_i [ pred_i == gold_i ]
p_e   = Σ_k (n_gold,k / N) · (n_pred,k / N)
kappa = (p_o − p_e) / (1 − p_e)
```

**Inputs:** `expected` (gold label, or the human rating) and the prediction from `label`, the arg-max of `probabilities`, or a short `output` (or the judge's verdict).

**How to read it**

−1 to 1. 0 is chance-level agreement, 1 is perfect, negative is systematic disagreement. A commonly quoted (and arbitrary) scale from Landis and Koch reads 0.41–0.60 as moderate, 0.61–0.80 as substantial and above 0.80 as almost perfect. For judge validation, compare the judge–human kappa with the human–human kappa on the same items.

**Use it when**

- Validating an LLM judge against human labels.
- Comparing classifiers on data where a high accuracy could be reached by following the label frequencies.

**Pitfalls**

- Prevalence paradox: with one dominant class, kappa can be near 0 while accuracy is 0.9 or higher. Nine `ok` samples predicted `ok` and one `spam` predicted `ok` give accuracy 0.9 and kappa 0.0.
- Unweighted. For ordinal ratings (1–5 scores) a near-miss counts as much as a far miss; consider correlations instead.
- Values depend on the label distribution, so kappas from datasets with different class balance are not comparable.
- Small samples give very wide uncertainty; look at the confidence interval.

**Example** (checked by the test suite against the real metric)

```jsonl
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "bug"}
{"expected": "bug", "label": "bug"}
{"expected": "bug", "label": "billing"}
{"expected": "refund", "label": "refund"}
{"expected": "refund", "label": "billing"}
{"expected": "refund", "label": "billing"}
```

Result: **0.3103**. p_o = 0.6, p_e = 0.5·0.7 + 0.2·0.2 + 0.3·0.1 = 0.42. Same as sklearn.metrics.cohen_kappa_score.

**Related:** [`accuracy`](#accuracy), [`mcc`](#mcc), [`balanced_accuracy`](#balanced_accuracy)

**References**

- Cohen, J. (1960). A Coefficient of Agreement for Nominal Scales. Educational and Psychological Measurement, 20(1), pp. 37–46. <https://doi.org/10.1177/001316446002000104>
- Feinstein, A. R., and Cicchetti, D. V. (1990). High agreement but low kappa: I. The problems of two paradoxes. Journal of Clinical Epidemiology, 43(6), pp. 543–549. <https://doi.org/10.1016/0895-4356(90)90158-L>
- Landis, J. R., and Koch, G. G. (1977). The Measurement of Observer Agreement for Categorical Data. Biometrics, 33(1), pp. 159–174. <https://doi.org/10.2307/2529310>

## f1

*The harmonic mean of precision and recall per label, averaged over labels (macro by default).*

**Level:** corpus · **Range:** 0 to 1, higher is better · **Needs:** `label`, `expected` · **Deterministic:** yes

**What it measures**

A balance of how trustworthy and how complete the model's labels are. Macro F1 answers "how well does the model handle each class, giving rare classes the same say as common ones?"

**How it is computed**

1. Read and normalise gold and predicted labels (trimmed, case-insensitive).
2. For every label in the union of gold and predicted labels, compute precision and recall (0 when undefined)
   and F1 = 2PR / (P + R) (0 when P + R = 0).
3. Combine according to `average`:
   - `macro` (default): unweighted mean of per-label F1 over the labels that appear in **gold**. Labels only
     ever predicted are excluded; this equals scikit-learn with `labels=` set to the gold labels.
   - `weighted`: mean of per-label F1 over gold labels, weighted by support.
   - `micro`: F1 of the pooled TP, FP and FN. For single-label classification this equals accuracy.
   - `binary`: F1 of the single label named by `positive`.
4. Note that macro F1 is the mean of per-label F1s, not the F1 of macro precision and macro recall.
5. Per-label precision, recall, F1, support and counts are returned in the details as `per_label`.

```text
F1_k     = 2 · P_k · R_k / (P_k + R_k)         (0 when P_k + R_k = 0)
macro    = (1/K) Σ_{k ∈ gold} F1_k
weighted = Σ_{k ∈ gold} support_k · F1_k / Σ support_k
micro    = 2 · P_micro · R_micro / (P_micro + R_micro)
binary   = F1_positive
```

**Inputs:** `expected` (gold label) and the prediction from `label`, the arg-max of `probabilities`, or a short `output`.

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `average` | `'macro'` | How per-label F1 is combined: `macro` (default; every gold class equal), `micro` (every sample equal; equals accuracy for single-label tasks), `weighted` (classes by frequency) or `binary` (one class, see `positive`). |
| `positive` | `'1'` | Label treated as the positive class when `average` is `binary` (default `"1"`). Compared case-insensitively; set it to your actual positive label. |

**How to read it**

0 to 1, higher is better. Macro F1 well below accuracy signals that rare classes are handled badly. Report which average you used: the same predictions can give quite different macro, weighted and micro values.

**Use it when**

- Classes are imbalanced and you care about each class (macro), or about a single positive class (binary).
- Both false positives and false negatives matter and you want one number.

**Pitfalls**

- Ignores true negatives, so in binary tasks it does not reward correctly rejecting negatives; `mcc` does.
- Macro F1 is sensitive to classes with very few samples; one sample can swing a class's F1 from 0 to 1.
- `binary` with the default `positive: "1"` gives 0 when your labels are words; set `positive`.
- Macro F1 here ignores predicted-only labels, which scikit-learn's default includes; numbers can differ when the model invents labels.

**Example** (checked by the test suite against the real metric)

```jsonl
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "bug"}
{"expected": "bug", "label": "bug"}
{"expected": "bug", "label": "billing"}
{"expected": "refund", "label": "refund"}
{"expected": "refund", "label": "billing"}
{"expected": "refund", "label": "billing"}
```

```yaml
metrics:
- name: f1
  params:
    average: macro
```

Result: **0.5556**. Per-label F1 is billing 0.667, bug 0.5, refund 0.5. Same as sklearn.metrics.f1_score(average='macro', zero_division=0); weighted gives 0.5833 and micro 0.6. Binary F1 is also checked against scikit-learn.

**Related:** [`precision_score`](#precision_score), [`recall_score`](#recall_score), [`accuracy`](#accuracy), [`mcc`](#mcc), [`balanced_accuracy`](#balanced_accuracy)

**References**

- Sokolova, M., and Lapalme, G. (2009). A systematic analysis of performance measures for classification tasks. Information Processing & Management, 45(4), pp. 427–437. <https://doi.org/10.1016/j.ipm.2009.03.002>
- Chicco, D., and Jurman, G. (2020). The advantages of the Matthews correlation coefficient (MCC) over F1 score and accuracy in binary classification evaluation. BMC Genomics, 21, article 6. <https://doi.org/10.1186/s12864-019-6413-7>

## label_match

*1 when the predicted label equals the gold label for this sample, else 0.*

**Level:** sample · **Range:** 0 to 1, higher is better · **Needs:** `label`, `expected` · **Deterministic:** yes

**What it measures**

Whether a single classification decision is right. It is the per-sample view of `accuracy`: the mean of `label_match` over a dataset equals `accuracy` on the same samples, but as a sample metric it can be sliced, filtered, thresholded and inspected row by row.

**How it is computed**

1. Read the gold label from `expected` (the first acceptable answer if several are given).
2. Read the prediction: `label` if set; otherwise the key of `probabilities` with the highest value; otherwise
   `output` when it is a string, number or boolean.
3. Trim surrounding whitespace from both and, unless `case_sensitive` is true, lowercase them.
4. Return 1.0 when they are identical, 0.0 otherwise. There is no partial credit and no synonym matching.

```text
label_match = 1   if norm(pred) == norm(gold)
            = 0   otherwise
norm(x) = lower(strip(x))        (strip(x) only when case_sensitive=true)
```

**Inputs:** `expected` (gold label) and a prediction from `label`, the arg-max of `probabilities`, or a short `output`. A sample with neither is skipped.

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `case_sensitive` | `False` | When true, `Billing` and `billing` are different labels. Default false, which suits most LLM classifiers whose capitalisation drifts. |

**How to read it**

Each sample scores 0 or 1. The run summary is the mean, i.e. accuracy. Use the per-sample scores to find which inputs fail, or slice by tag to get per-class accuracy (which is recall for that class).

**Use it when**

- You want per-row pass/fail for a classifier or router, e.g. to list the misrouted tickets.
- You need a gate on each sample (a threshold of 1 means "must be right").

**Pitfalls**

- Exact match only. If the model answers "Billing issue" for the label "billing", it scores 0; constrain the output format or map outputs to labels first.
- When `label` is absent the whole `output` string is used as the label, so a chatty answer never matches.
- Its mean hides class imbalance exactly as `accuracy` does; see `balanced_accuracy` and `f1`.

**Example** (checked by the test suite against the real metric)

```jsonl
{"expected": "Billing", "label": " billing"}
```

Result: **1**. Case and surrounding whitespace are ignored by default; with `case_sensitive=true` this scores 0.

**Related:** [`accuracy`](#accuracy), [`balanced_accuracy`](#balanced_accuracy), [`exact_match`](text.md#exact_match)

**References**

- Sokolova, M., and Lapalme, G. (2009). A systematic analysis of performance measures for classification tasks. Information Processing & Management, 45(4), pp. 427–437. <https://doi.org/10.1016/j.ipm.2009.03.002>

## mcc

*The Matthews correlation coefficient between predicted and gold labels, in its multi-class form.*

**Level:** corpus · **Range:** -1 to 1, higher is better · **Needs:** `label`, `expected` · **Deterministic:** yes

**What it measures**

The correlation between what the model predicts and what is true, using every cell of the confusion matrix (true and false positives and negatives for every class). It is high only when the model does well on all classes, which makes it one of the most informative single numbers under imbalance.

**How it is computed**

1. Read and normalise gold and predicted labels (trimmed, case-insensitive).
2. Build the K × K confusion matrix C over the union of gold and predicted labels (rows gold, columns predicted).
3. Compute Gorodkin's K-category correlation coefficient from the diagonal sum c, the total s, the per-class
   gold counts t_k and predicted counts p_k (formula below). For two classes this reduces to Matthews' binary MCC.
4. If the denominator is 0 (all gold labels or all predictions are one class), return 0.0, as scikit-learn does.

```text
c = Σ_k C_kk           s = Σ_ij C_ij
t_k = Σ_j C_kj (gold count of k)        p_k = Σ_i C_ik (predicted count of k)
MCC = (c·s − Σ_k p_k·t_k) / sqrt( (s² − Σ_k p_k²) · (s² − Σ_k t_k²) )
binary case: MCC = (TP·TN − FP·FN) / sqrt( (TP+FP)(TP+FN)(TN+FP)(TN+FN) )
```

**Inputs:** `expected` (gold label) and the prediction from `label`, the arg-max of `probabilities`, or a short `output`.

**How to read it**

−1 to 1 (in the multi-class case the lower bound lies between −1 and 0). 0 is no better than chance (including always predicting one class), 1 is perfect. Unlike F1 it rewards true negatives, and unlike accuracy it cannot be inflated by predicting the majority class.

**Use it when**

- Imbalanced classification, especially binary, where you need one number that cannot be gamed by the majority class.
- Comparing classifiers whose errors fall on different classes.

**Pitfalls**

- Harder to explain to non-specialists than accuracy or F1; report it with the confusion matrix.
- Returns 0 when the model predicts a single class for everything, even if that is right for most samples; this is intended but surprises people.
- With very few samples of a class the value is unstable.

**Example** (checked by the test suite against the real metric)

```jsonl
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "bug"}
{"expected": "bug", "label": "bug"}
{"expected": "bug", "label": "billing"}
{"expected": "refund", "label": "refund"}
{"expected": "refund", "label": "billing"}
{"expected": "refund", "label": "billing"}
```

Result: **0.3371**. Same as sklearn.metrics.matthews_corrcoef.

**Related:** [`cohen_kappa`](#cohen_kappa), [`f1`](#f1), [`balanced_accuracy`](#balanced_accuracy), [`accuracy`](#accuracy)

**References**

- Matthews, B. W. (1975). Comparison of the predicted and observed secondary structure of T4 phage lysozyme. Biochimica et Biophysica Acta (BBA) – Protein Structure, 405(2), pp. 442–451. <https://doi.org/10.1016/0005-2795(75)90109-9>
- Gorodkin, J. (2004). Comparing two K-category assignments by a K-category correlation coefficient. Computational Biology and Chemistry, 28(5–6), pp. 367–374. <https://doi.org/10.1016/j.compbiolchem.2004.09.006>
- Chicco, D., and Jurman, G. (2020). The advantages of the Matthews correlation coefficient (MCC) over F1 score and accuracy in binary classification evaluation. BMC Genomics, 21, article 6. <https://doi.org/10.1186/s12864-019-6413-7>

## precision_score

*Of the samples given a label, the share that truly have it, averaged over labels (macro by default).*

**Level:** corpus · **Range:** 0 to 1, higher is better · **Needs:** `label`, `expected` · **Deterministic:** yes

**What it measures**

How trustworthy the model's positive calls are. For one class it answers "when the model says *refund*, how often is it really a refund?" Averaging combines the classes into one number.

**How it is computed**

1. Read and normalise gold and predicted labels (trimmed, case-insensitive).
2. For every label in the union of gold and predicted labels, count TP, FP and FN and compute
   precision = TP / (TP + FP), taken as 0 when the label is never predicted.
3. Combine according to `average`:
   - `macro` (default): unweighted mean over the labels that appear in **gold**. Labels only ever predicted are
     left out (this equals scikit-learn with `labels=` set to the gold labels; scikit-learn's own default also
     includes predicted-only labels).
   - `weighted`: mean over gold labels weighted by their support (number of gold samples).
   - `micro`: pool TP and FP over all labels first. For single-label classification this equals accuracy.
   - `binary`: precision of the single label named by `positive` (0 if that label never occurs).
4. Per-label precision, recall, F1, support, TP, FP and FN are returned in the details as `per_label`.

```text
P_k      = TP_k / (TP_k + FP_k)                (0 when TP_k + FP_k = 0)
macro    = (1/K) Σ_{k ∈ gold} P_k
weighted = Σ_{k ∈ gold} support_k · P_k / Σ support_k
micro    = Σ_k TP_k / Σ_k (TP_k + FP_k)
binary   = P_positive
```

**Inputs:** `expected` (gold label) and the prediction from `label`, the arg-max of `probabilities`, or a short `output`.

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `average` | `'macro'` | How per-label precision is combined: `macro` (default), `micro`, `weighted` or `binary`. |
| `positive` | `'1'` | Label treated as the positive class when `average` is `binary` (default `"1"`). Compared case-insensitively; set it to your actual label, e.g. `spam`. |

**How to read it**

0 to 1, higher is better. High precision with low recall means the model is cautious: what it flags is right, but it misses many. Read the `per_label` details to find the class that pulls the average down.

**Use it when**

- False positives are costly (flagging a legitimate message as fraud, escalating a ticket wrongly).
- Paired with `recall_score` to see the trade-off behind an `f1` value.

**Pitfalls**

- A model that rarely predicts a class can have perfect precision on it while missing almost all of it; always read it with recall.
- With `binary`, a `positive` label that never appears silently gives 0. The default `"1"` is rarely right for text labels.
- Micro-averaged precision equals accuracy for single-label tasks, so it adds no information there.
- Unpredicted labels count as precision 0 (zero_division=0), which drags the macro average down.

**Example** (checked by the test suite against the real metric)

```jsonl
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "bug"}
{"expected": "bug", "label": "bug"}
{"expected": "bug", "label": "billing"}
{"expected": "refund", "label": "refund"}
{"expected": "refund", "label": "billing"}
{"expected": "refund", "label": "billing"}
```

Result: **0.6905**. Macro over billing 4/7, bug 1/2, refund 1/1. Same as sklearn.metrics.precision_score(average='macro', zero_division=0). Weighted gives 0.6857, micro 0.6.

**Related:** [`recall_score`](#recall_score), [`f1`](#f1), [`accuracy`](#accuracy)

**References**

- Sokolova, M., and Lapalme, G. (2009). A systematic analysis of performance measures for classification tasks. Information Processing & Management, 45(4), pp. 427–437. <https://doi.org/10.1016/j.ipm.2009.03.002>

## recall_score

*Of the samples that truly have a label, the share the model found, averaged over labels (macro by default).*

**Level:** corpus · **Range:** 0 to 1, higher is better · **Needs:** `label`, `expected` · **Deterministic:** yes

**What it measures**

How complete the model's coverage of each class is. For one class it answers "of all real refunds, how many did the model call a refund?" Macro-averaged recall is the same number as `balanced_accuracy`.

**How it is computed**

1. Read and normalise gold and predicted labels (trimmed, case-insensitive).
2. For every label, count TP and FN and compute recall = TP / (TP + FN), taken as 0 when the label has no gold samples.
3. Combine according to `average`:
   - `macro` (default): unweighted mean over the labels that appear in gold (equals `balanced_accuracy`).
   - `weighted`: mean over gold labels weighted by support. For single-label tasks this equals accuracy.
   - `micro`: pool TP and FN over all labels; for single-label tasks this also equals accuracy.
   - `binary`: recall of the label named by `positive`.
4. Per-label precision, recall, F1 and counts are returned in the details as `per_label`.

```text
R_k      = TP_k / (TP_k + FN_k)                (0 when TP_k + FN_k = 0)
macro    = (1/K) Σ_{k ∈ gold} R_k
weighted = Σ_{k ∈ gold} support_k · R_k / Σ support_k
micro    = Σ_k TP_k / Σ_k (TP_k + FN_k)
binary   = R_positive
```

**Inputs:** `expected` (gold label) and the prediction from `label`, the arg-max of `probabilities`, or a short `output`.

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `average` | `'macro'` | How per-label recall is combined: `macro` (default), `micro`, `weighted` or `binary`. |
| `positive` | `'1'` | Label treated as the positive class when `average` is `binary` (default `"1"`). Compared case-insensitively. |

**How to read it**

0 to 1, higher is better. Low recall on a class means the model misses it, typically by sending it to a larger neighbouring class; the confusion matrix in `accuracy`'s details shows where it goes.

**Use it when**

- Misses are costly (an urgent ticket not flagged, harmful content not caught).
- Paired with `precision_score` to understand an `f1` value.

**Pitfalls**

- Predicting a class for everything gives that class recall 1; read it with precision.
- Weighted and micro recall both equal accuracy in single-label classification, so they inherit accuracy's imbalance problem.
- With `binary`, a wrong `positive` label silently gives 0.

**Example** (checked by the test suite against the real metric)

```jsonl
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "billing"}
{"expected": "billing", "label": "bug"}
{"expected": "bug", "label": "bug"}
{"expected": "bug", "label": "billing"}
{"expected": "refund", "label": "refund"}
{"expected": "refund", "label": "billing"}
{"expected": "refund", "label": "billing"}
```

Result: **0.5444**. Macro over billing 4/5, bug 1/2, refund 1/3. Same as sklearn.metrics.recall_score(average='macro', zero_division=0). Weighted and micro both give 0.6 (the accuracy).

**Related:** [`precision_score`](#precision_score), [`f1`](#f1), [`balanced_accuracy`](#balanced_accuracy)

**References**

- Sokolova, M., and Lapalme, G. (2009). A systematic analysis of performance measures for classification tasks. Information Processing & Management, 45(4), pp. 427–437. <https://doi.org/10.1016/j.ipm.2009.03.002>
