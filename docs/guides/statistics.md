---
title: Statistics
description: Confidence intervals for every metric, paired comparisons with multiple-testing correction, and planning how many samples you need.
---

# Statistics

An evaluation is a sample of what your system will meet. A score of 0.82 on 40 questions could easily be 0.74 or 0.90
on the next 40. Guage Kit reports how uncertain each number is, and calls a change between two runs real only when the
data supports it. Everything is plain Python with a fixed seed, so a report regenerates exactly.

## Confidence intervals

Every metric summary has a 95% interval (`ci_low`, `ci_high`; set `confidence` to change the level):

- **Sample metrics**: percentile bootstrap of the mean over samples (`n_resamples=1000` by default, `seed=0`).
- **Corpus metrics** (BLEU, F1, ECE, …): the samples are resampled with replacement and the metric is recomputed on
  each resample (up to 200 times), and the interval is the percentiles of those values. It is left empty when the
  metric is non-deterministic, when there are fewer than 2 or more than 20,000 samples, or when too few resamples give
  a value (for example, resamples with a single class).

The summary also carries mean, median, standard deviation, min, max, a 10-bin histogram and, with a threshold, the
pass rate.

```python
from guage_kit import stats
stats.bootstrap_ci(values, confidence=0.95, n_resamples=2000, seed=0)
```

## Comparing two runs

`guage compare A B` (or `guage_kit.compare(a, b)`) pairs the two runs' samples by id. Pairing removes the variation
between questions, which is usually the largest source of noise, so paired tests detect much smaller differences than
comparing two means.

For each sample-level metric both runs share:

| Statistic | What it is |
| --- | --- |
| `delta` | mean of (candidate − baseline) per sample |
| `ci_low`, `ci_high` | paired bootstrap interval of that mean (2,000 resamples) |
| `p_value` | two-sided paired permutation (sign-flip) test; exact when 2ⁿ ≤ 10,000 differing pairs, Monte Carlo with 10,000 draws otherwise |
| `p_adjusted` | Holm–Bonferroni adjustment across all the metrics tested together |
| `wins`, `losses`, `ties` | samples where the candidate scored higher, lower or the same (the sign test) |
| `effect_size` | paired Cohen's d: mean difference ÷ standard deviation of the differences |

Each metric gets a **direction** (respecting whether higher or lower is better):

| Direction | Rule |
| --- | --- |
| `improved` / `regressed` | adjusted p ≤ `alpha` (0.05) and the change is larger than `min_effect` |
| `unchanged` | not significant, the interval is narrower than 0.05, and the change is within `max(min_effect, 0.01)`: there is evidence of no meaningful difference |
| `inconclusive` | anything else: the data can't tell. Usually it needs more samples |

**Corpus metrics** have no per-sample values to pair. They get the difference only, and their direction is `changed`
(or `unchanged` when the change is within `min_effect`): Guage Kit reports the movement but never calls it
significant. Gate them with `max_drop` if a change of a given size must fail the build.

The comparison also lists the samples that moved most in each direction, with both outputs side by side, and
whether the runs used the same inputs (`same_data`, from the [input fingerprint](datasets.md#fingerprints)).

```bash
guage compare baseline:main latest --min-effect 0.02 --fail-on-regression -o comparison.html
```

### Why Holm?

Testing twelve metrics at α = 0.05 gives roughly a 46% chance that at least one shows a "significant" change by
luck alone. Holm's step-down correction controls that family-wise error rate while staying more powerful than plain
Bonferroni. It is conservative when metrics are correlated, as they often are (token F1 and ROUGE-L move together),
and that is the safe side to err on for a release decision.

### Example: why the demo uses 72 samples

The demo compares two versions of a support assistant. With 24 questions, the quality metrics all moved in the
right direction (faithfulness +0.20, token F1 +0.18), yet after Holm correction none of them was significant
(adjusted p of 0.9 or more).
With each question asked in three phrasings (72 samples), the same kind of improvement is clearly detected:

| metric | before | after | Δ | 95% CI | p (Holm) | direction |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| faithfulness | 0.549 | 0.822 | 0.273 | 0.125 – 0.412 | 0.009 | improved |
| token_f1 | 0.580 | 0.814 | 0.234 | 0.090 – 0.368 | 0.010 | improved |
| recall@3 | 0.681 | 0.875 | 0.194 | 0.042 – 0.333 | 0.065 | inconclusive |

The lesson generalises: small test sets can't confirm moderate improvements. Plan the size before you trust a
comparison.

## Planning sample size

```python
from guage_kit import stats

stats.samples_needed(0.05, 0.2)          # 126: to detect a +0.05 mean change when per-sample differences have SD 0.2
stats.min_detectable_effect(0.2, 72)     # 0.066: the smallest change 72 paired samples detect reliably
```

Both assume a paired comparison at 95% confidence and 80% power (`confidence` 0.90/0.95/0.99, `power` 0.8/0.9/0.95).
Estimate the standard deviation of differences from a previous comparison: the per-sample deltas are in the
comparison report.

## The functions

`guage_kit.stats` exposes `mean`, `median`, `stdev`, `quantile`, `histogram`, `bootstrap_ci`, `paired_bootstrap`,
`permutation_test`, `sign_test`, `wilcoxon` (signed-rank, normal approximation with tie and continuity correction),
`cohens_d`, `holm`, `min_detectable_effect` and `samples_needed`.

```python
from guage_kit import stats
a = [0.62, 0.70, 0.55, 0.81, 0.66, 0.74, 0.59, 0.68]
b = [0.71, 0.78, 0.60, 0.80, 0.75, 0.83, 0.64, 0.77]
print(stats.paired_bootstrap(a, b))
print(stats.permutation_test(a, b))
print(stats.sign_test(a, b))
```

```text
{'delta': 0.06624999999999999, 'ci_low': 0.04125000000000001, 'ci_high': 0.08499999999999998, 'p_better': 1.0}
0.015625
{'wins': 7, 'losses': 1, 'ties': 0, 'p_value': 0.0703125}
```

The sign test ignores how big each difference is, so it is less powerful than the permutation test on the same data.
The sign test, Wilcoxon, the binomial p-value and the correlations are tested against SciPy.
