from typing import List
import numpy as np
from scipy.stats import bootstrap

def mean_with_ci(data: List[float], n_resamples: int = 1000, alpha: float = 0.05) -> dict:
    """Calculate the mean and bootstrap confidence interval of the given data.

    Args:
        data (List[float]): The input data for which to calculate the mean and CI.
        n_resamples (int): The number of bootstrap resamples to perform.
        alpha (float): The significance level for the confidence interval.

    Returns:
        dict: A dictionary containing the mean and the confidence interval.
    """
    mean = np.mean(data)
    ci = bootstrap((data,), np.mean, n_resamples=n_resamples, confidence_level=1-alpha)
    return {"mean": mean, "ci_lower": ci.confidence_interval.low, "ci_upper": ci.confidence_interval.high}

def score_metrics(metrics: List[float]) -> float:
    """Calculate a simple score based on the provided metrics.

    Args:
        metrics (List[float]): A list of metric values.

    Returns:
        float: The calculated score.
    """
    return np.mean(metrics)  # Example scoring function, can be modified as needed.