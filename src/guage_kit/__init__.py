"""Guage Kit: measure LLMs, RAG pipelines, retrieval, embeddings, classifiers and agents.

Quick start::

    import guage_kit as gk

    run = gk.evaluate("qa.jsonl", ["token_f1", "faithfulness", "recall@5"], gates=[{"metric": "faithfulness", "min": 0.8}])
    print(run.gate.verdict)
    gk.report(run, "report.html")

The public API is re-exported here; everything else is importable from its module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from guage_kit.core import (
    Dataset,
    GateResult,
    GateRule,
    MetricSummary,
    RunResult,
    Sample,
    SampleResult,
    Score,
    ToolCall,
    Usage,
    load_dataset,
)
from guage_kit.errors import GuageError
from guage_kit.metrics.registry import MetricContext, corpus_metric, metric
from guage_kit.version import __version__

if TYPE_CHECKING:
    from pathlib import Path


def evaluate(*args: Any, **kwargs: Any) -> RunResult:
    """Evaluate a dataset (see :func:`guage_kit.runner.evaluate.evaluate`)."""
    from guage_kit.runner.evaluate import evaluate as _evaluate

    return _evaluate(*args, **kwargs)


def compare(a: Any, b: Any, **kwargs: Any) -> Any:
    """Compare two runs (see :func:`guage_kit.runner.compare.compare`). Accepts runs, run ids or paths."""
    from guage_kit.runner.compare import compare as _compare
    from guage_kit.runner.store import load_run

    return _compare(load_run(a), load_run(b), **kwargs)


def report(result: Any, path: str | Path, **kwargs: Any) -> Path:
    """Write an offline HTML report for a run or a comparison."""
    from guage_kit.reports import write_report

    return write_report(result, path, **kwargs)


def list_metrics(family: str | None = None) -> list[dict[str, Any]]:
    """Every metric's declaration: name, family, required fields, parameters."""
    from guage_kit.metrics.registry import list_metrics as _list

    return _list(family)


__all__ = [
    "Dataset",
    "GateResult",
    "GateRule",
    "GuageError",
    "MetricContext",
    "MetricSummary",
    "RunResult",
    "Sample",
    "SampleResult",
    "Score",
    "ToolCall",
    "Usage",
    "__version__",
    "compare",
    "corpus_metric",
    "evaluate",
    "list_metrics",
    "load_dataset",
    "metric",
    "report",
]
