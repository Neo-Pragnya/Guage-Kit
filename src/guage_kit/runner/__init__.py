"""Running evaluations: targets, the evaluation engine, run storage and comparisons."""

from guage_kit.runner.compare import Comparison, compare, pairwise, regression_gate
from guage_kit.runner.evaluate import auto_metrics, evaluate
from guage_kit.runner.store import RunStore, load_run
from guage_kit.runner.target import ProviderTarget, Target, make_target

__all__ = [
    "Comparison",
    "ProviderTarget",
    "RunStore",
    "Target",
    "auto_metrics",
    "compare",
    "evaluate",
    "load_run",
    "make_target",
    "pairwise",
    "regression_gate",
]
