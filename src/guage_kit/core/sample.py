"""The sample: one thing to evaluate.

A sample holds whatever the metrics need. Most fields are optional: a text metric reads ``output`` and ``expected``,
a retrieval metric reads ``retrieved_ids`` and ``relevant_ids``, an agent metric reads ``tool_calls`` or ``trace``.
Each metric declares the fields it requires, and a sample without them is skipped with a reason, never scored as 0.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolCall(BaseModel):
    """A tool (function) call an agent made, or one it was expected to make."""

    model_config = ConfigDict(extra="forbid")

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    output: Any = None
    error: str | None = None


class Usage(BaseModel):
    """Token usage and cost for producing a sample's output."""

    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost_usd: float | None = None

    @property
    def tokens(self) -> int | None:
        if self.total_tokens is not None:
            return self.total_tokens
        if self.prompt_tokens is None and self.completion_tokens is None:
            return None
        return (self.prompt_tokens or 0) + (self.completion_tokens or 0)


class Sample(BaseModel):
    """One evaluation sample. Unknown fields in files are kept in ``metadata`` by the dataset loader."""

    model_config = ConfigDict(extra="forbid")

    id: str
    input: Any = ""
    output: Any = None
    expected: Any = None
    references: list[str] = Field(default_factory=list)

    # retrieval and RAG
    contexts: list[str] = Field(default_factory=list)
    retrieved_ids: list[str] = Field(default_factory=list)
    relevant_ids: list[str] = Field(default_factory=list)
    relevance: dict[str, float] = Field(default_factory=dict)  # graded relevance, id -> gain

    # classification and calibration
    label: str | None = None  # predicted label (defaults to output when output is a short string)
    probabilities: dict[str, float] = Field(default_factory=dict)
    confidence: float | None = None

    # embeddings
    embeddings: dict[str, list[float]] = Field(default_factory=dict)

    # agents
    tool_calls: list[ToolCall] = Field(default_factory=list)
    expected_tool_calls: list[ToolCall] = Field(default_factory=list)
    trace: dict[str, Any] | None = None  # an Ananke AgentTrace (or any trace Ananke can normalise)

    # runtime
    latency_ms: float | None = None
    usage: Usage | None = None

    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # ── convenience views ──────────────────────────────────────────────────
    @property
    def output_text(self) -> str:
        return _as_text(self.output)

    @property
    def input_text(self) -> str:
        return _as_text(self.input)

    @property
    def expected_texts(self) -> list[str]:
        """Every acceptable reference answer: ``expected`` (when text) followed by ``references``."""
        texts: list[str] = []
        if isinstance(self.expected, list):
            texts.extend(_as_text(e) for e in self.expected)
        elif self.expected is not None:
            texts.append(_as_text(self.expected))
        texts.extend(r for r in self.references if r not in texts)
        return texts

    @property
    def predicted_label(self) -> str | None:
        if self.label is not None:
            return self.label
        if self.probabilities:
            return max(self.probabilities, key=lambda k: self.probabilities[k])
        if isinstance(self.output, (str, int, bool)):
            return str(self.output).strip()
        return None

    def has(self, field: str) -> bool:
        """Whether the field a metric needs is present and non-empty."""
        if field == "expected":
            return bool(self.expected_texts)
        if field == "label":
            return self.predicted_label is not None
        if field == "output":
            return self.output is not None and self.output != ""
        value = getattr(self, field, None)
        if value is None:
            return False
        if isinstance(value, (list, dict, str)):
            return len(value) > 0
        return True


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if (
        isinstance(value, list)
        and value
        and all(isinstance(m, dict) and "content" in m for m in value)
    ):
        # chat messages: the conversation text
        return "\n".join(str(m.get("content", "")) for m in value)
    if isinstance(value, dict):
        for key in ("text", "content", "answer", "output"):
            if isinstance(value.get(key), str):
                return str(value[key])
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


__all__ = ["Sample", "ToolCall", "Usage"]
