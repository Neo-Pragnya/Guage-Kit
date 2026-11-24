from __future__ import annotations

import random

import pytest
from scipy import stats as sps

from guage_kit import stats


def test_bootstrap_ci_is_reproducible_and_covers_the_mean() -> None:
    rng = random.Random(0)
    xs = [rng.random() for _ in range(200)]
    a = stats.bootstrap_ci(xs, seed=1)
    b = stats.bootstrap_ci(xs, seed=1)
    assert a == b
    assert a[0] < stats.mean(xs) < a[1]
    assert stats.bootstrap_ci([0.5]) == (0.5, 0.5)


def test_permutation_exact_small_case() -> None:
    # all four differences positive: only the all-plus and all-minus sign patterns are as extreme
    assert stats.permutation_test([0, 0, 0, 0], [1, 1, 1, 1]) == pytest.approx(2 / 16)
    assert stats.permutation_test([1, 2], [1, 2]) == 1.0


def test_sign_test_matches_scipy_binomtest() -> None:
    a = [0.0] * 10
    b = [1, 1, 1, 1, 1, 1, 1, -1, -1, 0]
    st = stats.sign_test(a, b)
    assert (st["wins"], st["losses"], st["ties"]) == (7, 2, 1)
    assert st["p_value"] == pytest.approx(sps.binomtest(2, 9, 0.5).pvalue)


def test_wilcoxon_close_to_scipy_normal_approximation() -> None:
    rng = random.Random(4)
    a = [rng.gauss(0, 1) for _ in range(60)]
    b = [x + rng.gauss(0.3, 1) for x in a]
    ours = stats.wilcoxon(a, b)["p_value"]
    ref = sps.wilcoxon(b, a, correction=True, method="approx").pvalue
    assert ours == pytest.approx(ref, rel=0.02)


def test_holm_adjustment() -> None:
    out = stats.holm({"a": 0.01, "b": 0.04, "c": 0.03}, alpha=0.05)
    assert out["a"]["p_adjusted"] == pytest.approx(0.03)
    assert out["c"]["p_adjusted"] == pytest.approx(0.06)
    assert out["b"]["p_adjusted"] == pytest.approx(0.06)
    assert out["a"]["significant"] and not out["c"]["significant"]


def test_paired_bootstrap_and_effect_size() -> None:
    a = [0.5] * 50
    b = [0.6] * 50
    pb = stats.paired_bootstrap(a, b)
    assert pb["delta"] == pytest.approx(0.1)
    assert pb["p_better"] == 1.0
    assert stats.cohens_d([0, 0, 0], [1, 2, 3]) == pytest.approx(2.0)


def test_sample_size_planning() -> None:
    n = stats.samples_needed(0.05, 0.2)
    assert n == 126
    assert stats.min_detectable_effect(0.2, n) <= 0.05 + 1e-9
    with pytest.raises(ValueError):
        stats.samples_needed(0, 1)


def test_quantile_histogram() -> None:
    assert stats.quantile([1, 2, 3, 4], 0.5) == 2.5
    counts, rng = stats.histogram([0, 0.5, 1], 2, 0, 1)
    assert counts == [1, 2] and rng == (0, 1)
