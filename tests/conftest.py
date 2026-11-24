from __future__ import annotations

from typing import Any

import pytest

import guage_kit.metrics  # noqa: F401  (registers the built-ins)
from guage_kit.core.sample import Sample
from guage_kit.metrics.registry import MetricContext, resolve
from guage_kit.metrics.semantic import HashingEmbedder

pytest_plugins = ["pytester"]


def score(metric: str, ctx: MetricContext | None = None, **fields: Any) -> float | None:
    fields.setdefault("id", "s")
    return (
        resolve(metric)
        .score(Sample(**fields), ctx or MetricContext(embedder=HashingEmbedder()))
        .value
    )


def corpus(
    metric: str, samples: list[Sample], ctx: MetricContext | None = None, **params: Any
) -> Any:
    return resolve({"name": metric, "params": params}).compute(
        samples, ctx or MetricContext(embedder=HashingEmbedder())
    )


@pytest.fixture
def rag_samples() -> list[Sample]:
    return [
        Sample(
            id="q1",
            input="What is the capital of France?",
            output="Paris is the capital of France [1].",
            expected="Paris",
            contexts=["Paris is the capital and largest city of France.", "Berlin is in Germany."],
            retrieved_ids=["d1", "d2"],
            relevant_ids=["d1"],
            tags=["geo"],
            metadata={"difficulty": "easy"},
        ),
        Sample(
            id="q2",
            input="Who wrote Hamlet?",
            output="Hamlet was written by Christopher Marlowe in 1720.",
            expected="William Shakespeare wrote Hamlet.",
            contexts=["Hamlet is a tragedy written by William Shakespeare around 1600."],
            retrieved_ids=["d9", "d3"],
            relevant_ids=["d3"],
            tags=["lit"],
            metadata={"difficulty": "hard"},
        ),
        Sample(
            id="q3",
            input="What is the boiling point of water at sea level?",
            output="100 degrees Celsius.",
            expected="100 degrees Celsius",
            contexts=["Water boils at 100 degrees Celsius at sea level."],
            retrieved_ids=["d5"],
            relevant_ids=["d5"],
            tags=["sci"],
            metadata={"difficulty": "easy"},
        ),
    ]
