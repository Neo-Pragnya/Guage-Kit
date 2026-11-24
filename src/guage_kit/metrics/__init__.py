"""Metrics. Importing this package registers every built-in family and Ananke's agent evaluators."""

from guage_kit.metrics import (  # noqa: F401  (each module registers its metrics)
    agent,
    classification,
    embeddings,
    judged,
    rag,
    retrieval,
    runtime,
    safety,
    semantic,
    structured,
    text,
)
from guage_kit.metrics.registry import (
    REGISTRY,
    BoundMetric,
    CorpusOutput,
    MetricContext,
    MetricInfo,
    corpus_metric,
    get_metric,
    list_metrics,
    metric,
    resolve,
)


def _register_ananke() -> int:
    try:
        from guage_kit.harness.catalogue import register_all

        return register_all()
    except (
        ImportError
    ):  # pragma: no cover - ananke-plexus is a hard dependency; guard against a broken install
        return 0


ANANKE_EVALUATORS = _register_ananke()

__all__ = [
    "ANANKE_EVALUATORS",
    "REGISTRY",
    "BoundMetric",
    "CorpusOutput",
    "MetricContext",
    "MetricInfo",
    "corpus_metric",
    "get_metric",
    "list_metrics",
    "metric",
    "resolve",
]
