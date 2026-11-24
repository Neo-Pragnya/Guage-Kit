---
title: "Statistical methods"
description: "What each statistical method computes, what it assumes, and the papers behind it."
---

# Statistical methods

Every number in a Guage Kit run comes with an interval, and every comparison with a test that accounts for
testing many metrics at once. All methods are implemented in plain Python with a fixed seed, so a report can be
regenerated exactly. Function signatures are in the [statistics API](statistics.md).

## Percentile bootstrap confidence interval

`guage_kit.stats.bootstrap_ci`

Resamples the per-sample scores with replacement (2,000 times by default, fixed seed), recomputes the statistic each time and reports the 2.5th and 97.5th percentiles. Makes no normality assumption; needs the samples to be representative and independent. Corpus metrics are recomputed on each resample.

**References**

- Efron, B. (1979). Bootstrap Methods: Another Look at the Jackknife. The Annals of Statistics, 7(1), 1–26. [doi.org](https://doi.org/10.1214/aos/1176344552)
- Efron, B. and Tibshirani, R. J. (1993). An Introduction to the Bootstrap. Chapman & Hall/CRC. [doi.org](https://doi.org/10.1201/9780429246593)

## Paired bootstrap of a difference

`guage_kit.stats.paired_bootstrap`

Resamples sample ids (not scores) so both systems are compared on the same resampled items, giving an interval for mean(b − a) and the share of resamples in which b beats a.

**References**

- Koehn, P. (2004). Statistical Significance Tests for Machine Translation Evaluation. Proceedings of EMNLP 2004, pp. 388–395. [aclanthology.org](https://aclanthology.org/W04-3250/)
- Berg-Kirkpatrick, T., Burkett, D. and Klein, D. (2012). An Empirical Investigation of Statistical Significance in NLP. Proceedings of EMNLP-CoNLL 2012, pp. 995–1005. [aclanthology.org](https://aclanthology.org/D12-1091/)

## Paired permutation (sign-flip) test

`guage_kit.stats.permutation_test`

Under the null hypothesis the sign of each paired difference is arbitrary; the p-value is the share of sign assignments whose mean difference is at least as extreme as the observed one. Enumerates all 2^n assignments when that is at most `n_resamples` (exact), otherwise samples them. This is the test `guage compare` reports.

**References**

- Fisher, R. A. (1935). The Design of Experiments. Oliver and Boyd.
- Dror, R., Baumer, G., Shlomov, S. and Reichart, R. (2018). The Hitchhiker's Guide to Testing Statistical Significance in Natural Language Processing. Proceedings of ACL 2018, pp. 1383–1392. [aclanthology.org](https://aclanthology.org/P18-1128/)

## Sign test

`guage_kit.stats.sign_test`

Counts wins and losses of b over a (ties dropped) and computes an exact two-sided binomial p-value. Uses only the direction of each difference, so it is robust to outliers but has less power.

**References**

- Dixon, W. J. and Mood, A. M. (1946). The Statistical Sign Test. Journal of the American Statistical Association, 41(236), 557–566. [doi.org](https://doi.org/10.1080/01621459.1946.10501898)

## Wilcoxon signed-rank test

`guage_kit.stats.wilcoxon`

Ranks the absolute paired differences and compares the rank sums of positive and negative differences, with the normal approximation, tie correction and continuity correction. More powerful than the sign test when differences are roughly symmetric.

**References**

- Wilcoxon, F. (1945). Individual Comparisons by Ranking Methods. Biometrics Bulletin, 1(6), 80–83. [doi.org](https://doi.org/10.2307/3001968)

## Holm–Bonferroni correction

`guage_kit.stats.holm`

When many metrics are compared at once, some will look significant by chance. Holm's step-down procedure sorts the p-values, multiplies the i-th smallest by (m − i + 1), enforces monotonicity and controls the family-wise error rate at `alpha` without assuming independence.

**References**

- Holm, S. (1979). A Simple Sequentially Rejective Multiple Test Procedure. Scandinavian Journal of Statistics, 6(2), 65–70. [www.jstor.org](https://www.jstor.org/stable/4615733)

## Cohen's d (paired)

`guage_kit.stats.cohens_d`

Mean of the paired differences divided by their standard deviation: how large a change is relative to its noise, independent of sample size. Roughly 0.2 is small, 0.5 medium and 0.8 large.

**References**

- Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences (2nd ed.). Lawrence Erlbaum Associates. [doi.org](https://doi.org/10.4324/9780203771587)

## Minimum detectable effect and sample size

`guage_kit.stats.min_detectable_effect`

From the standard deviation of paired differences, the smallest true mean difference a paired test of n samples detects with the given power (normal approximation), and the inverse: how many samples a given effect needs. Use it before building a dataset.

**References**

- Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences (2nd ed.). Lawrence Erlbaum Associates. [doi.org](https://doi.org/10.4324/9780203771587)

## Quantiles and percentiles

`guage_kit.stats.quantile`

Linear interpolation between order statistics (Hyndman and Fan type 7), used for latency percentiles.

**References**

- Hyndman, R. J. and Fan, Y. (1996). Sample Quantiles in Statistical Packages. The American Statistician, 50(4), 361–365. [doi.org](https://doi.org/10.1080/00031305.1996.10473566)
