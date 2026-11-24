"""Targets: the system under test. Guage Kit calls it for every sample that has no output yet.

A target is any callable. It receives the sample's ``input`` (or the whole :class:`Sample` when its first
parameter is named ``sample`` or annotated ``Sample``) and returns either the output text, or a dict that can also
carry ``contexts``, ``retrieved_ids``, ``tool_calls``, ``label``, ``probabilities``, ``confidence``, ``usage``,
``trace`` and ``metadata``. That is how a RAG pipeline reports what it retrieved and an agent reports what it did.

Targets can also be named: ``module:function`` imports your function; a provider spec (``anthropic:claude-opus-5-5``,
``ollama:llama3.1`` …) calls a model with an optional system prompt and prompt template.
"""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from typing import Any

from guage_kit.core.sample import Sample, ToolCall, Usage
from guage_kit.errors import GuageError
from guage_kit.judges.providers import Provider, import_object, make_provider

_PROVIDER_KINDS = ("anthropic", "openai", "ollama", "openai-compatible", "bedrock")


class Target:
    def __init__(
        self,
        fn: Callable[..., Any],
        *,
        name: str | None = None,
        retries: int = 0,
        backoff_s: float = 1.0,
    ) -> None:
        self.fn = fn
        self.name = name or getattr(fn, "__qualname__", getattr(fn, "__name__", "target"))
        self.retries = retries
        self.backoff_s = backoff_s
        self.wants_sample = _wants_sample(fn)

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": "callable", "retries": self.retries}

    def __call__(self, sample: Sample) -> Sample:
        """Run the target on a sample and return a copy with the output (and whatever else it reported)."""
        attempt = 0
        while True:
            start = time.perf_counter()
            try:
                raw = self.fn(sample) if self.wants_sample else self.fn(sample.input)
                elapsed = (time.perf_counter() - start) * 1000
                return merge_output(sample, raw, elapsed)
            except Exception as exc:
                if attempt >= self.retries:
                    raise GuageError(
                        "GK-TARGET-002",
                        f"target failed on sample {sample.id}: {type(exc).__name__}: {exc}",
                    ) from exc
                time.sleep(self.backoff_s * (2**attempt))
                attempt += 1


class ProviderTarget(Target):
    """Call a model directly: ``template`` formats the prompt from the sample (``{input}``, ``{contexts}``, metadata keys)."""

    def __init__(
        self,
        provider: str | Provider,
        *,
        system: str = "You are a helpful assistant.",
        template: str = "{input}",
        retries: int = 2,
    ) -> None:
        self.provider = make_provider(provider)
        self.system = system
        self.template = template

        def call(sample: Sample) -> dict[str, Any]:
            fields = {
                **{k: v for k, v in sample.metadata.items() if isinstance(v, (str, int, float))},
                "input": sample.input_text,
                "contexts": "\n\n".join(sample.contexts),
            }
            completion = self.provider.complete(
                self.system, self.template.format_map(_Default(fields))
            )
            return {
                "output": completion.text,
                "usage": {
                    "prompt_tokens": completion.input_tokens,
                    "completion_tokens": completion.output_tokens,
                },
                "metadata": {"model": completion.model},
            }

        super().__init__(call, name=self.provider.name, retries=retries)
        self.wants_sample = True

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": "provider",
            "system": self.system,
            "template": self.template,
        }


class _Default(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _wants_sample(fn: Callable[..., Any]) -> bool:
    try:
        params = list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        return False
    if not params:
        return False
    p = params[0]
    return p.name == "sample" or p.annotation in (Sample, "Sample")


def merge_output(sample: Sample, raw: Any, elapsed_ms: float | None = None) -> Sample:
    if isinstance(raw, Sample):
        out = raw
        if out.latency_ms is None and elapsed_ms is not None:
            out = out.model_copy(update={"latency_ms": elapsed_ms})
        return out
    update: dict[str, Any] = {}
    if isinstance(raw, dict) and (
        {"output", "answer", "text", "label", "tool_calls", "contexts"} & set(raw)
    ):
        update["output"] = raw.get("output", raw.get("answer", raw.get("text")))
        for key in (
            "contexts",
            "retrieved_ids",
            "label",
            "probabilities",
            "confidence",
            "trace",
            "embeddings",
        ):
            if key in raw:
                update[key] = raw[key]
        if "tool_calls" in raw:
            update["tool_calls"] = [
                c if isinstance(c, ToolCall) else ToolCall.model_validate(c)
                for c in raw["tool_calls"]
            ]
        if "usage" in raw and raw["usage"] is not None:
            update["usage"] = (
                raw["usage"]
                if isinstance(raw["usage"], Usage)
                else Usage.model_validate(raw["usage"])
            )
        if raw.get("latency_ms") is not None:
            update["latency_ms"] = float(raw["latency_ms"])
        if isinstance(raw.get("metadata"), dict):
            update["metadata"] = {**sample.metadata, **raw["metadata"]}
    else:
        update["output"] = raw
    if "latency_ms" not in update and elapsed_ms is not None:
        update["latency_ms"] = elapsed_ms
    return sample.model_copy(update=update)


def make_target(spec: Any, **options: Any) -> Target | None:
    """A callable, ``module:function``, a provider spec, or an existing :class:`Target`."""
    if spec is None:
        return None
    if isinstance(spec, Target):
        return spec
    if callable(spec):
        return Target(
            spec, **{k: v for k, v in options.items() if k in ("name", "retries", "backoff_s")}
        )
    if isinstance(spec, str):
        kind = spec.partition(":")[0]
        if kind in _PROVIDER_KINDS:
            return ProviderTarget(
                spec, **{k: v for k, v in options.items() if k in ("system", "template", "retries")}
            )
        import sys
        from pathlib import Path

        # your own code in the current folder is importable, as `python -m` would see it
        if str(Path.cwd()) not in sys.path:
            sys.path.insert(0, str(Path.cwd()))
        fn = import_object(spec.removeprefix("python:"))
        if not callable(fn):
            raise GuageError("GK-TARGET-001", f"{spec} is not callable")
        return Target(
            fn, name=spec, **{k: v for k, v in options.items() if k in ("retries", "backoff_s")}
        )
    raise GuageError("GK-TARGET-001", f"cannot use {type(spec).__name__} as a target")


__all__ = ["ProviderTarget", "Target", "make_target", "merge_output"]
