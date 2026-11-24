---
title: "Probes and synthetic data"
description: "Perturbations, robustness runs, red-team datasets and test sets generated from your documents."
---

# Probes and synthetic data

> [!NOTE]
> Generated from the code by `scripts/gen_api_docs.py`; signatures and docstrings are the installed
> package's.

The perturbation kinds are listed in [perturbations](perturbations.md).

## `guage_kit.probes`

Probes: does the system hold up when inputs change, and does it resist misuse?

**Robustness.** `perturb` makes variants of each input (typos, casing, spacing, punctuation, filler, a
distracting sentence, shuffled or degraded retrieval context). `robustness` runs the target on the original
and every variant and reports, per perturbation, how often the answer stays the same (output agreement) and how much
each metric drops.

**Red team.** `redteam_dataset` builds a safety test set in the project's own words: direct and indirect
prompt injection with a canary token, system-prompt extraction, personal-data extraction and over-refusal checks
(benign requests that merely sound risky). Score it with `injection_resistance`, `system_prompt_leakage`,
`pii_leakage` and `refusal_correctness`.

### `PERTURBATIONS`

```python
PERTURBATIONS = {'typos': ..., 'uppercase': ..., 'lowercase': ..., 'no_punctuation': ..., 'whitespace': ..., 'filler': ..., 'distractor': ..., 'shuffle_contexts': ..., 'drop_top_context': ..., 'noise_context': ...}
```

### `PERTURBATION_DESCRIPTIONS`

```python
PERTURBATION_DESCRIPTIONS = {'typos': "Introduces typing errors in about 6% of the input's letters: swapped neighbours, dropped letters and neighbouring-key substitutions.", 'uppercase': 'Turns the whole input into capitals.', 'lowercase': 'Turns the whole input into lower case.', 'no_punctuation': 'Removes every punctuation c …
```

### `canary`

```python
canary() -> str
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/probes/__init__.py#L225)

A fresh random canary token (`GK-CANARY-XXXXXXXX`): planted in red-team prompts so a leak is detectable
without false positives.

### `perturb`

```python
perturb(
    dataset: Dataset,
    kinds: Sequence[str] = ('typos', 'lowercase', 'filler', 'distractor'),
    *,
    seed: int = 0,
) -> Dataset
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/probes/__init__.py#L142)

Variants of every sample. Each variant's id is `<id>~<kind>` and `metadata.perturbation` names the kind.

### `redteam_dataset`

```python
redteam_dataset(
    *,
    system_prompt: str | None = None,
    benign_context: str = 'Our store opens at 9am and closes at 6pm, Monday to Saturday.',
    seed: int = 0,
) -> Dataset
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/probes/__init__.py#L260)

A safety probe set. Run your target on it and score with the safety metrics (`metrics=None` picks them).

### `robustness`

```python
robustness(
    dataset: Dataset,
    target: Any,
    *,
    kinds: Sequence[str] = ('typos', 'lowercase', 'filler', 'distractor'),
    metrics: Sequence[str] | None = None,
    seed: int = 0,
    concurrency: int = 4,
) -> dict[str, Any]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/probes/__init__.py#L168)

Run the target on the originals and their variants; report agreement and metric drops per perturbation.

## `guage_kit.synth`

Synthetic test sets from your own documents.

`chunk` splits documents into overlapping passages with stable ids. `cloze_dataset` makes offline,
deterministic fill-in-the-blank questions: a sentence with a key span (a number or a proper noun) blanked out, the
span as the answer, and the source passage as the relevant context. That exercises retrieval and grounded answering
with no model at all. `generate_qa` asks a model for natural questions instead, grounded in each passage and
returned as JSON (questions it cannot ground are dropped).

### `chunk`

```python
chunk(
    documents: Sequence[tuple[str, str]],
    *,
    size: int = 120,
    overlap: int = 20,
) -> list[dict[str, str]]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/synth/__init__.py#L48)

Word-window chunks: `{"id", "source", "text"}`. Ids hash the source, offset and text, so re-chunking is stable.

### `cloze_dataset`

```python
cloze_dataset(
    chunks: Sequence[dict[str, str]],
    *,
    per_chunk: int = 1,
    seed: int = 0,
    name: str = 'synthetic-cloze',
) -> Dataset
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/synth/__init__.py#L70)

Offline test questions from document chunks: a salient term is blanked out of a sentence and becomes
the expected answer, with the chunk as context and its id as the relevant document.

### `generate_qa`

```python
generate_qa(
    chunks: Sequence[dict[str, str]],
    provider: Any,
    *,
    per_chunk: int = 2,
    name: str = 'synthetic-qa',
) -> Dataset
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/synth/__init__.py#L118)

Natural questions from a model (any provider spec or object), grounded and checked against each passage.

### `read_documents`

```python
read_documents(paths: Iterable[str | Path]) -> list[tuple[str, str]]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/synth/__init__.py#L25)

(name, text) for every .md, .txt, .rst and .html file under the given paths.

### `write_corpus`

```python
write_corpus(chunks: Sequence[dict[str, str]], path: str | Path) -> Path
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/synth/__init__.py#L183)

Save chunks as JSON Lines, the corpus a retriever under test indexes.
