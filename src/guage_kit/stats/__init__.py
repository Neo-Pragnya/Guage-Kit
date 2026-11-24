"""Statistics for evaluation: is a number trustworthy, and is a difference real?

- :func:`bootstrap_ci` — percentile bootstrap confidence interval of a statistic (seeded, reproducible);
- :func:`paired_bootstrap` — distribution of the mean difference between two systems on the same samples;
- :func:`permutation_test` — paired sign-flip permutation test (exact for small n);
- :func:`sign_test` and :func:`wilcoxon` — non-parametric paired tests;
- :func:`cohens_d` — paired effect size; :func:`holm` — Holm–Bonferroni correction over many metrics;
- :func:`min_detectable_effect` and :func:`samples_needed` — how big a dataset must be to see a difference.

Everything is plain Python with a fixed seed, so a report can be regenerated exactly.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from itertools import product
from typing import Any


def mean(xs: Sequence[float]) -> float:
    """Arithmetic mean (NaN for an empty sequence)."""
    return sum(xs) / len(xs) if xs else float("nan")


def stdev(xs: Sequence[float]) -> float:
    """Sample standard deviation (n − 1 denominator); 0 for fewer than two values."""
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def median(xs: Sequence[float]) -> float:
    """Median (NaN for an empty sequence)."""
    s = sorted(xs)
    n = len(s)
    if not n:
        return float("nan")
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quantile(xs: Sequence[float], q: float) -> float:
    """Quantile ``q`` in [0, 1] by linear interpolation between order statistics (type 7 in Hyndman and Fan,
    1996; the default of NumPy and R)."""
    s = sorted(xs)
    if not s:
        return float("nan")
    idx = (len(s) - 1) * q
    lo = math.floor(idx)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])


def bootstrap_ci(
    values: Sequence[float],
    *,
    statistic: Callable[[Sequence[float]], float] = mean,
    confidence: float = 0.95,
    n_resamples: int = 2000,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile bootstrap interval for ``statistic`` of ``values``."""
    n = len(values)
    if n == 0:
        return (float("nan"), float("nan"))
    if n == 1:
        return (values[0], values[0])
    rng = random.Random(seed)
    stats = sorted(
        statistic([values[rng.randrange(n)] for _ in range(n)]) for _ in range(n_resamples)
    )
    alpha = (1 - confidence) / 2
    return quantile(stats, alpha), quantile(stats, 1 - alpha)


def histogram(
    values: Sequence[float], bins: int = 10, lo: float | None = None, hi: float | None = None
) -> tuple[list[int], tuple[float, float]]:
    """Counts of values in ``bins`` equal-width bins over [lo, hi] (the data's range by default), and the range used."""
    if not values:
        return [], (0.0, 0.0)
    a = min(values) if lo is None else lo
    b = max(values) if hi is None else hi
    if b <= a:
        b = a + 1e-9
    counts = [0] * bins
    for v in values:
        i = int((v - a) / (b - a) * bins)
        counts[min(max(i, 0), bins - 1)] += 1
    return counts, (a, b)


# ── paired comparisons ───────────────────────────────────────────────────────────────────────────────────────────
def paired_bootstrap(
    a: Sequence[float],
    b: Sequence[float],
    *,
    confidence: float = 0.95,
    n_resamples: int = 2000,
    seed: int = 0,
) -> dict[str, float]:
    """Mean of (b − a), its bootstrap interval, and the share of resamples where b beats a."""
    d = [y - x for x, y in zip(a, b, strict=True)]
    n = len(d)
    if n == 0:
        return {
            "delta": float("nan"),
            "ci_low": float("nan"),
            "ci_high": float("nan"),
            "p_better": float("nan"),
        }
    rng = random.Random(seed)
    means = sorted(mean([d[rng.randrange(n)] for _ in range(n)]) for _ in range(n_resamples))
    alpha = (1 - confidence) / 2
    return {
        "delta": mean(d),
        "ci_low": quantile(means, alpha),
        "ci_high": quantile(means, 1 - alpha),
        "p_better": sum(1 for m in means if m > 0) / len(means),
    }


def permutation_test(
    a: Sequence[float], b: Sequence[float], *, n_resamples: int = 10000, seed: int = 0
) -> float:
    """Two-sided paired permutation (sign-flip) test of mean(b − a) = 0. Exact when 2^n ≤ n_resamples."""
    d = [y - x for x, y in zip(a, b, strict=True) if y != x]
    n = len(d)
    if n == 0:
        return 1.0
    observed = abs(sum(d))
    if 2**n <= n_resamples:
        hits = sum(
            1
            for signs in product((1, -1), repeat=n)
            if abs(sum(s * x for s, x in zip(signs, d, strict=True))) >= observed - 1e-12
        )
        return float(hits / 2**n)
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_resamples):
        if abs(sum(x if rng.random() < 0.5 else -x for x in d)) >= observed - 1e-12:
            hits += 1
    return (hits + 1) / (n_resamples + 1)


def _binom_two_sided(k: int, n: int) -> float:
    if n == 0:
        return 1.0
    probs = [math.comb(n, i) / 2**n for i in range(n + 1)]
    pk = probs[k]
    return float(min(1.0, sum(p for p in probs if p <= pk + 1e-15)))


def sign_test(a: Sequence[float], b: Sequence[float]) -> dict[str, float]:
    """Wins, losses and ties of b over a, with an exact two-sided binomial p-value (ties dropped)."""
    wins = sum(1 for x, y in zip(a, b, strict=True) if y > x)
    losses = sum(1 for x, y in zip(a, b, strict=True) if y < x)
    ties = len(a) - wins - losses
    return {
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "p_value": _binom_two_sided(min(wins, losses), wins + losses),
    }


def _norm_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2))


def wilcoxon(a: Sequence[float], b: Sequence[float]) -> dict[str, float]:
    """Wilcoxon signed-rank test (normal approximation with tie and continuity correction)."""
    d = [y - x for x, y in zip(a, b, strict=True) if y != x]
    n = len(d)
    if n == 0:
        return {"statistic": 0.0, "p_value": 1.0, "n": 0}
    absd = [abs(x) for x in d]
    order = sorted(range(n), key=lambda i: absd[i])
    ranks = [0.0] * n
    i = 0
    tie_term = 0.0
    while i < n:
        j = i
        while j + 1 < n and absd[order[j + 1]] == absd[order[i]]:
            j += 1
        r = (i + j) / 2 + 1
        t = j - i + 1
        tie_term += t**3 - t
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    w_plus = sum(r for r, x in zip(ranks, d, strict=True) if x > 0)
    mu = n * (n + 1) / 4
    sigma = math.sqrt(n * (n + 1) * (2 * n + 1) / 24 - tie_term / 48)
    if sigma == 0:
        return {"statistic": w_plus, "p_value": 1.0, "n": n}
    z = (abs(w_plus - mu) - 0.5) / sigma
    return {"statistic": w_plus, "p_value": min(1.0, 2 * _norm_sf(max(z, 0.0))), "n": n}


def cohens_d(a: Sequence[float], b: Sequence[float]) -> float:
    """Paired effect size: mean difference ÷ standard deviation of the differences."""
    d = [y - x for x, y in zip(a, b, strict=True)]
    s = stdev(d)
    m = mean(d) if d else 0.0
    if s == 0:
        return 0.0 if m == 0 else math.copysign(float("inf"), m)
    return m / s


def holm(p_values: dict[str, float], alpha: float = 0.05) -> dict[str, dict[str, Any]]:
    """Holm–Bonferroni: adjusted p-values and which hypotheses are rejected when testing many metrics at once."""
    items = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(items)
    out: dict[str, dict[str, Any]] = {}
    running = 0.0
    still = True
    for i, (k, p) in enumerate(items):
        adj = min(1.0, max(running, (m - i) * p))
        running = adj
        rejected = still and adj <= alpha
        if not rejected:
            still = False
        out[k] = {"p_value": p, "p_adjusted": adj, "significant": rejected}
    return out


_Z = {0.90: 1.6449, 0.95: 1.96, 0.99: 2.5758}
_ZP = {0.8: 0.8416, 0.9: 1.2816, 0.95: 1.6449}


def min_detectable_effect(
    sd_diff: float, n: int, *, confidence: float = 0.95, power: float = 0.8
) -> float:
    """Smallest true mean difference a paired comparison of n samples detects with the given power."""
    if n <= 0:
        return float("inf")
    return (_Z.get(confidence, 1.96) + _ZP.get(power, 0.8416)) * sd_diff / math.sqrt(n)


def samples_needed(
    effect: float, sd_diff: float, *, confidence: float = 0.95, power: float = 0.8
) -> int:
    """Samples needed to detect a mean paired difference of ``effect``."""
    if effect <= 0:
        raise ValueError("effect must be positive")
    return math.ceil(((_Z.get(confidence, 1.96) + _ZP.get(power, 0.8416)) * sd_diff / effect) ** 2)


__all__ = [
    "bootstrap_ci",
    "cohens_d",
    "histogram",
    "holm",
    "mean",
    "median",
    "min_detectable_effect",
    "paired_bootstrap",
    "permutation_test",
    "quantile",
    "samples_needed",
    "sign_test",
    "stdev",
    "wilcoxon",
]
