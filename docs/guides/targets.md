---
title: Targets
description: Let Guage Kit call the system under test - a Python function, an importable path or a model - and record what it retrieved, called and spent.
---

# Targets

A target is the system under test. When you pass one, Guage Kit calls it for every sample **that has no output
yet**, measures the latency, and scores what comes back. Samples that already have an output are left alone, so a
dataset can mix recorded and live outputs.

## A function

```python
import guage_kit as gk

def answer(question: str) -> dict:
    # your pipeline here: retrieve, then generate
    docs = {"kb-sync": "The app syncs every 30 seconds when you are online."}
    return {"output": "It syncs every 30 seconds.", "contexts": list(docs.values()),
            "retrieved_ids": list(docs), "usage": {"prompt_tokens": 120, "completion_tokens": 9}}

data = [gk.Sample(id="q1", input="How often does it sync?", expected="Every 30 seconds.",
                  relevant_ids=["kb-sync"])]
run = gk.evaluate(data, ["faithfulness", "context_recall", "recall@3", "total_tokens"], target=answer)
print({k: round(v.value, 3) for k, v in run.summaries.items()})
print(run.samples[0].output, run.samples[0].latency_ms is not None)
```

```text
{'faithfulness': 1.0, 'context_recall': 1.0, 'recall@3': 1.0, 'total_tokens': 129.0}
It syncs every 30 seconds. True
```

### What a target may return

- **Text** (or any value): becomes `output`.
- **A dict** with `output` (or `answer` or `text`), and optionally `contexts`, `retrieved_ids`, `label`,
  `probabilities`, `confidence`, `trace`, `embeddings`, `tool_calls` (list of dicts or `ToolCall`), `usage`,
  `latency_ms` (overrides the measured time) and `metadata` (merged into the sample's). This is how a RAG pipeline
  reports what it retrieved and an agent reports what it did.
- **A `Sample`**: used as is (latency is filled in when missing).

### What a target receives

The sample's `input`. If the function's first parameter is named `sample` or annotated `Sample`, it receives the
whole sample instead, which is useful when the system needs metadata:

```python
def answer(sample: gk.Sample) -> str:
    return my_bot.reply(sample.input, user_tier=sample.metadata.get("tier"))
```

## An importable path

In `guage.yaml` or on the command line, name the function as `module:function` (or `module.function`). The module
must be importable from the working directory or your environment:

```yaml
target: support_bot.pipeline:answer
```

```bash
guage run --data data/qa.jsonl --target support_bot.pipeline:answer
```

## A model directly

A provider spec calls a model with a system prompt and a prompt template. The template is formatted with `{input}`,
`{contexts}` (joined with blank lines) and any text or number in the sample's metadata:

```yaml
target: anthropic:claude-opus-5-5
target_options:
  system: "You answer questions about Lumen Notes in one sentence."
  template: "Context:\n{contexts}\n\nQuestion: {input}"
```

Supported specs are the same as for judges: `anthropic:`, `openai:`, `ollama:`, `openai-compatible:<url>#<model>`,
`bedrock:` and `python:module:function`. See [Judges](judges.md#providers). Token usage and the model name are
recorded on each sample. This needs network access and credentials.

In Python: `from guage_kit.runner import ProviderTarget; ProviderTarget("ollama:llama3.1", system=..., template=...)`.

## Concurrency, retries and repeats

| Option | Default | Effect |
| --- | --- | --- |
| `concurrency` (`evaluate`, suite) | 4 | number of samples run at once (threads). Also used for judge-backed metrics |
| retries (`Target(fn, retries=N, backoff_s=1.0)`; provider targets default to 2) | 0 | retry a failing call with exponential backoff |
| `repeats` (`evaluate`, suite, `guage run --repeats`) | 1 | run the target several times per sample |

With `repeats > 1`, the first output is scored. The others are kept in the report, and a `self_consistency` metric
(mean pairwise token F1 between the repeated outputs) shows how stable the system is on the same input.

```python
from guage_kit.runner import Target
run = gk.evaluate(data, ["token_f1"], target=Target(answer, retries=2), repeats=3, concurrency=8)
```

## When the target fails

A sample whose target call raises (after retries) gets a `target_error`, appears in the report, and is left out of
every metric. The run carries a note such as "the target failed on 1 of 2 samples". Failures never become zero
scores that drag a mean down silently. A target that cannot be imported is a `GK-TARGET-001` error before anything
runs.
