---
title: "Statistics"
description: "Bootstrap intervals, paired tests, multiple-comparison correction, effect sizes and sample-size planning."
---

# Statistics

> [!NOTE]
> Generated from the code by `scripts/gen_api_docs.py`; signatures and docstrings are the installed
> package's.

See [statistical methods](statistical-methods.md) for what each method assumes and the papers behind it, and the [statistics guide](../../guides/statistics.md) for how runs use them.

## `guage_kit.stats`

Statistics for evaluation: is a number trustworthy, and is a difference real?

- `bootstrap_ci` — percentile bootstrap confidence interval of a statistic (seeded, reproducible);
- `paired_bootstrap` — distribution of the mean difference between two systems on the same samples;
- `permutation_test` — paired sign-flip permutation test (exact for small n);
- `sign_test` and `wilcoxon` — non-parametric paired tests;
- `cohens_d` — paired effect size; `holm` — Holm–Bonferroni correction over many metrics;
- `min_detectable_effect` and `samples_needed` — how big a dataset must be to see a difference.

Everything is plain Python with a fixed seed, so a report can be regenerated exactly.

### `bootstrap_ci`

```python
bootstrap_ci(
    values: Sequence[float],
    *,
    statistic: Callable[[Sequence[float]], float] = mean,
    confidence: float = 0.95,
    n_resamples: int = 2000,
    seed: int = 0,
) -> tuple[float, float]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L56)

Percentile bootstrap interval for `statistic` of `values`.

### `cohens_d`

```python
cohens_d(a: Sequence[float], b: Sequence[float]) -> float
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L204)

Paired effect size: mean difference ÷ standard deviation of the differences.

### `histogram`

```python
histogram(
    values: Sequence[float],
    bins: int = 10,
    lo: float | None = None,
    hi: float | None = None,
) -> tuple[list[int], tuple[float, float]]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L78)

Counts of values in `bins` equal-width bins over [lo, hi] (the data's range by default), and the range used.

### `holm`

```python
holm(p_values: dict[str, float], alpha: float = 0.05) -> dict[str, dict[str, Any]]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L214)

Holm–Bonferroni: adjusted p-values and which hypotheses are rejected when testing many metrics at once.

### `mean`

```python
mean(xs: Sequence[float]) -> float
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L22)

Arithmetic mean (NaN for an empty sequence).

### `median`

```python
median(xs: Sequence[float]) -> float
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L35)

Median (NaN for an empty sequence).

### `min_detectable_effect`

```python
min_detectable_effect(
    sd_diff: float,
    n: int,
    *,
    confidence: float = 0.95,
    power: float = 0.8,
) -> float
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L235)

Smallest true mean difference a paired comparison of n samples detects with the given power.

### `paired_bootstrap`

```python
paired_bootstrap(
    a: Sequence[float],
    b: Sequence[float],
    *,
    confidence: float = 0.95,
    n_resamples: int = 2000,
    seed: int = 0,
) -> dict[str, float]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L96)

Mean of (b − a), its bootstrap interval, and the share of resamples where b beats a.

### `permutation_test`

```python
permutation_test(
    a: Sequence[float],
    b: Sequence[float],
    *,
    n_resamples: int = 10000,
    seed: int = 0,
) -> float
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L125)

Two-sided paired permutation (sign-flip) test of mean(b − a) = 0. Exact when 2^n ≤ n_resamples.

### `quantile`

```python
quantile(xs: Sequence[float], q: float) -> float
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L44)

Quantile `q` in [0, 1] by linear interpolation between order statistics (type 7 in Hyndman and Fan,
1996; the default of NumPy and R).

### `samples_needed`

```python
samples_needed(
    effect: float,
    sd_diff: float,
    *,
    confidence: float = 0.95,
    power: float = 0.8,
) -> int
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L244)

Samples needed to detect a mean paired difference of `effect`.

### `sign_test`

```python
sign_test(a: Sequence[float], b: Sequence[float]) -> dict[str, float]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L157)

Wins, losses and ties of b over a, with an exact two-sided binomial p-value (ties dropped).

### `stdev`

```python
stdev(xs: Sequence[float]) -> float
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L27)

Sample standard deviation (n − 1 denominator); 0 for fewer than two values.

### `wilcoxon`

```python
wilcoxon(a: Sequence[float], b: Sequence[float]) -> dict[str, float]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/stats/__init__.py#L174)

Wilcoxon signed-rank test (normal approximation with tie and continuity correction).
