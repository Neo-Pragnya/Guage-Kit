"""Model providers for judges and targets.

A provider turns a system prompt and a user prompt into text. Spec strings pick one:

==========================================  ======================================================================
``anthropic:<model>``                       Claude through the official ``anthropic`` SDK (``guage-kit[anthropic]``)
``openai:<model>``                          OpenAI's chat completions API (``OPENAI_API_KEY``), over plain HTTP
``ollama:<model>``                          a local Ollama server (OpenAI-compatible endpoint on port 11434)
``openai-compatible:<base-url>#<model>``    any OpenAI-compatible server: vLLM, LM Studio, llama.cpp, gateways
``bedrock:<model-id>``                      Amazon Bedrock's Converse API (``guage-kit[bedrock]``)
``python:<module>:<function>``              your own function ``fn(system, prompt) -> str``
==========================================  ======================================================================

Keys come from the environment (``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY``, or ``GUAGE_OPENAI_COMPATIBLE_KEY``),
never from configuration files.
"""

from __future__ import annotations

import importlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from guage_kit.errors import GuageError

DEFAULT_ANTHROPIC_MODEL = "claude-opus-5-5"


@dataclass
class Completion:
    text: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    stop_reason: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Provider(Protocol):
    """The protocol a judge or target provider implements: a ``name`` and ``complete(system, prompt, json_schema=None)``
    returning a :class:`Completion`."""

    name: str

    def complete(
        self, system: str, prompt: str, *, json_schema: dict[str, Any] | None = None
    ) -> Completion: ...


# ── Anthropic (official SDK) ─────────────────────────────────────────────────────────────────────────────────────
class AnthropicProvider:
    """Claude via the ``anthropic`` SDK. Server-side refusal fallbacks are on by default (``fallbacks=False`` to
    turn them off); structured outputs guarantee a JSON verdict when a schema is given."""

    def __init__(
        self,
        model: str = DEFAULT_ANTHROPIC_MODEL,
        *,
        max_tokens: int = 16000,
        effort: str | None = None,
        fallbacks: bool = True,
        client: Any = None,
    ) -> None:
        if client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise GuageError(
                    "GK-JUDGE-001",
                    "the anthropic SDK is not installed",
                    hint="pip install 'guage-kit[anthropic]'",
                ) from exc
            client = anthropic.Anthropic()
        self._client = client
        self.model = model
        self.max_tokens = max_tokens
        self.effort = effort
        self.fallbacks = fallbacks
        self.name = f"anthropic:{model}"

    def complete(
        self, system: str, prompt: str, *, json_schema: dict[str, Any] | None = None
    ) -> Completion:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        output_config: dict[str, Any] = {}
        if json_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": json_schema}
        if self.effort:
            output_config["effort"] = self.effort
        if output_config:
            kwargs["output_config"] = output_config
        start = time.monotonic()
        try:
            if self.fallbacks:
                response = self._client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs
                )
            else:
                response = self._client.messages.create(**kwargs)
        except Exception as exc:
            raise GuageError("GK-JUDGE-003", f"{self.name}: {type(exc).__name__}: {exc}") from exc
        elapsed = (time.monotonic() - start) * 1000
        stop = str(getattr(response, "stop_reason", "") or "")
        text = "".join(
            getattr(b, "text", "") for b in response.content if getattr(b, "type", "") == "text"
        )
        if stop == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None) if details else None
            raise GuageError(
                "GK-JUDGE-003",
                f"{self.name} declined to judge (refusal{', ' + str(category) if category else ''})",
            )
        usage = getattr(response, "usage", None)
        return Completion(
            text=text,
            model=str(getattr(response, "model", self.model)),
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            latency_ms=elapsed,
            stop_reason=stop,
        )


# ── OpenAI-compatible (plain HTTP via httpx, which Ananke already depends on) ─────────────────────────────────────
class OpenAICompatibleProvider:
    """A provider for any server that speaks the OpenAI-compatible chat completions API
    (hosted services, vLLM, LM Studio, llama.cpp server …). Uses the standard library only."""

    def __init__(
        self,
        model: str,
        *,
        base_url: str = "https://api.openai.com/v1",
        api_key: str | None = None,
        timeout: float = 120.0,
        name: str | None = None,
        max_tokens: int = 4096,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.name = name or f"openai-compatible:{self.base_url}#{model}"

    def complete(
        self, system: str, prompt: str, *, json_schema: dict[str, Any] | None = None
    ) -> Completion:
        import httpx

        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self.max_tokens,
        }
        if json_schema is not None:
            body["response_format"] = {"type": "json_object"}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        start = time.monotonic()
        try:
            r = httpx.post(
                f"{self.base_url}/chat/completions",
                json=body,
                headers=headers,
                timeout=self.timeout,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            raise GuageError("GK-JUDGE-003", f"{self.name}: {type(exc).__name__}: {exc}") from exc
        choice = (data.get("choices") or [{}])[0]
        usage = data.get("usage") or {}
        return Completion(
            text=str((choice.get("message") or {}).get("content") or ""),
            model=str(data.get("model") or self.model),
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
            latency_ms=(time.monotonic() - start) * 1000,
            stop_reason=str(choice.get("finish_reason") or ""),
        )


# ── Amazon Bedrock (Converse API through boto3) ──────────────────────────────────────────────────────────────────
class BedrockProvider:
    """A provider for models on Amazon Bedrock through the Converse API (needs the ``bedrock`` extra)."""

    def __init__(self, model: str, *, region: str | None = None, max_tokens: int = 4096) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise GuageError(
                "GK-JUDGE-001", "boto3 is not installed", hint="pip install 'guage-kit[bedrock]'"
            ) from exc
        self._client = boto3.client("bedrock-runtime", region_name=region)
        self.model = model
        self.max_tokens = max_tokens
        self.name = f"bedrock:{model}"

    def complete(
        self, system: str, prompt: str, *, json_schema: dict[str, Any] | None = None
    ) -> Completion:
        start = time.monotonic()
        try:
            resp = self._client.converse(
                modelId=self.model,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": self.max_tokens},
            )
        except Exception as exc:
            raise GuageError("GK-JUDGE-003", f"{self.name}: {type(exc).__name__}: {exc}") from exc
        content = resp.get("output", {}).get("message", {}).get("content", [])
        usage = resp.get("usage", {})
        return Completion(
            text="".join(c.get("text", "") for c in content),
            model=self.model,
            input_tokens=int(usage.get("inputTokens") or 0),
            output_tokens=int(usage.get("outputTokens") or 0),
            latency_ms=(time.monotonic() - start) * 1000,
            stop_reason=str(resp.get("stopReason") or ""),
        )


class CallableProvider:
    """Wrap ``fn(system, prompt) -> str`` (or ``-> Completion``) as a provider: your own client, a mock, a cache."""

    def __init__(self, fn: Callable[[str, str], Any], name: str = "python") -> None:
        self._fn = fn
        self.name = name

    def complete(
        self, system: str, prompt: str, *, json_schema: dict[str, Any] | None = None
    ) -> Completion:
        start = time.monotonic()
        out = self._fn(system, prompt)
        if isinstance(out, Completion):
            return out
        if isinstance(out, dict):
            out = json.dumps(out)
        return Completion(
            text=str(out), model=self.name, latency_ms=(time.monotonic() - start) * 1000
        )


def import_object(path: str) -> Any:
    """Import ``package.module:attr`` (or ``package.module.attr``)."""
    module, sep, attr = path.partition(":")
    if not sep:
        module, _, attr = path.rpartition(".")
    if not module or not attr:
        raise GuageError("GK-TARGET-001", f"cannot import {path!r}", hint="use module:function")
    try:
        # the user names their own code in their own configuration
        # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
        obj: Any = importlib.import_module(module)
        for part in attr.split("."):
            obj = getattr(obj, part)
    except (ImportError, AttributeError) as exc:
        raise GuageError("GK-TARGET-001", f"cannot import {path!r}: {exc}") from exc
    return obj


def make_provider(spec: str | Provider, **options: Any) -> Provider:
    """Build a provider from a spec string (see the module docs) or return a provider as is."""
    if not isinstance(spec, str):
        return spec
    kind, _, rest = spec.partition(":")
    if kind == "anthropic":
        return AnthropicProvider(rest or DEFAULT_ANTHROPIC_MODEL, **options)
    if kind == "openai":
        if not rest:
            raise GuageError("GK-JUDGE-001", "openai: needs a model name", hint="openai:<model>")
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise GuageError("GK-JUDGE-001", "OPENAI_API_KEY is not set")
        return OpenAICompatibleProvider(rest, api_key=key, name=spec, **options)
    if kind == "ollama":
        base = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/") + "/v1"
        return OpenAICompatibleProvider(rest or "llama3.1", base_url=base, name=spec, **options)
    if kind == "openai-compatible":
        base, _, model = rest.rpartition("#")
        if not base or not model:
            raise GuageError(
                "GK-JUDGE-001", f"bad spec {spec!r}", hint="openai-compatible:<base-url>#<model>"
            )
        return OpenAICompatibleProvider(
            model,
            base_url=base,
            api_key=os.environ.get("GUAGE_OPENAI_COMPATIBLE_KEY"),
            name=spec,
            **options,
        )
    if kind == "bedrock":
        return BedrockProvider(rest, **options)
    if kind == "python":
        return CallableProvider(import_object(rest), name=spec)
    raise GuageError(
        "GK-JUDGE-001",
        f"unknown provider {kind!r}",
        hint="anthropic:, openai:, ollama:, openai-compatible:, bedrock: or python:",
    )


__all__ = [
    "DEFAULT_ANTHROPIC_MODEL",
    "AnthropicProvider",
    "BedrockProvider",
    "CallableProvider",
    "Completion",
    "OpenAICompatibleProvider",
    "Provider",
    "import_object",
    "make_provider",
]
