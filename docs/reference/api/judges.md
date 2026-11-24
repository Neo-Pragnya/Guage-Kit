---
title: "Judges and providers"
description: "LLM and heuristic judges, criteria, calibration against human labels, and model providers."
---

# Judges and providers

> [!NOTE]
> Generated from the code by `scripts/gen_api_docs.py`; signatures and docstrings are the installed
> package's.

A judge grades samples on a [criterion](criteria.md). `make_judge('heuristic')` works offline; `make_judge('anthropic:claude-opus-5-5')` and the other provider specs use a model.

## `guage_kit.judges.judge`

Judges: graded, pairwise and entailment verdicts, from a model or from transparent heuristics.

`LLMJudge` asks a model. Its prompts keep the trusted rubric in the system prompt and put every piece of
evaluated content (question, answer, reference, context) inside clearly marked untrusted blocks, with an instruction
to treat them as data, which is the same trusted/untrusted split as Ananke's judge envelope. Verdicts are requested as
JSON (with the provider's structured-output mode when it has one), parsed defensively, and cached on disk by a
hash of the prompt, so re-running an evaluation costs nothing. `samples=n` asks n times and averages
(self-consistency). Pairwise comparisons run in both orders and call a tie when the verdicts disagree, which
neutralises position bias.

`HeuristicJudge` answers the same questions offline, deterministically, from lexical signals. It exists so
that pipelines, tests and demos run without a model. Its verdicts are not a substitute for a real judge.

### `BaseJudge`

```python
class BaseJudge() -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/judge.py#L62)

The judge interface: `grade` a sample on a criterion, `entailment` of a hypothesis by a premise, and
`pairwise` comparison of two outputs. Tracks token usage across calls.

- **`BaseJudge.grade(sample: Sample, criterion: str | dict[str, Any] | Criterion) -> Verdict`**
- **`BaseJudge.entailment(*, premise: str, hypothesis: str) -> float`**
- **`BaseJudge.pairwise(
    *,
    question: str,
    a: str,
    b: str,
    criterion: str | Criterion = 'helpfulness',
    reference: str | None = None,
) -> PairwiseVerdict`**
- **`BaseJudge.describe() -> dict[str, Any]`**

### `HeuristicJudge`

```python
class HeuristicJudge() -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/judge.py#L305)

Offline, deterministic stand-in for a model judge (lexical signals per criterion).

- **`HeuristicJudge.grade(sample: Sample, criterion: str | dict[str, Any] | Criterion) -> Verdict`**
- **`HeuristicJudge.entailment(*, premise: str, hypothesis: str) -> float`**
- **`HeuristicJudge.pairwise(
    *,
    question: str,
    a: str,
    b: str,
    criterion: str | Criterion = 'helpfulness',
    reference: str | None = None,
) -> PairwiseVerdict`**

### `JudgeUsage`

```python
class JudgeUsage(
    calls: int = 0,
    cache_hits: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    errors: int = 0,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/judge.py#L50)

JudgeUsage(calls: 'int' = 0, cache_hits: 'int' = 0, input_tokens: 'int' = 0, output_tokens: 'int' = 0, errors: 'int' = 0)

- **`JudgeUsage.as_dict() -> dict[str, int]`**

### `LLMJudge`

```python
class LLMJudge(
    provider: str | Provider,
    *,
    samples: int = 1,
    cache_dir: str | Path | None = '.guage/cache/judge',
    provider_options: dict[str, Any] | None = None,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/judge.py#L177)

A judge backed by a model provider (`anthropic:<model>`, `openai:<model>`, `ollama:<model>` …).

Prompts put sample text inside untrusted blocks, responses are parsed as JSON, results are cached on disk
(`cache_dir`), `samples > 1` averages several independent grades (self-consistency), and pairwise
comparisons are run in both orders to cancel position bias.

- **`LLMJudge.grade(sample: Sample, criterion: str | dict[str, Any] | Criterion) -> Verdict`**
- **`LLMJudge.entailment(*, premise: str, hypothesis: str) -> float`**
- **`LLMJudge.pairwise(
    *,
    question: str,
    a: str,
    b: str,
    criterion: str | Criterion = 'helpfulness',
    reference: str | None = None,
) -> PairwiseVerdict`**

### `PairwiseVerdict`

```python
class PairwiseVerdict(
    winner: Literal['a', 'b', 'tie'],
    consistent: bool,
    reason: str = '',
    raw: list[str] = <factory>,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/judge.py#L42)

PairwiseVerdict(winner: "Literal['a', 'b', 'tie']", consistent: 'bool', reason: 'str' = '', raw: 'list[str]' = <factory>)


### `Verdict`

```python
class Verdict(
    score: float,
    raw_score: float | None = None,
    reason: str = '',
    samples: list[float] = <factory>,
    cached: bool = False,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/judge.py#L33)

Verdict(score: 'float', raw_score: 'float | None' = None, reason: 'str' = '', samples: 'list[float]' = <factory>, cached: 'bool' = False)


### `grade_prompt`

```python
grade_prompt(sample: Sample, criterion: Criterion) -> str
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/judge.py#L108)

The grading prompt for a sample and criterion: the rubric, then the question, answer, reference and
contexts, each inside a delimited untrusted block.

### `make_judge`

```python
make_judge(spec: str | BaseJudge | Provider | None, **options: Any) -> BaseJudge | None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/judge.py#L383)

`"heuristic"` → `HeuristicJudge`; a provider spec (`anthropic:claude-opus-5-5`) or provider →
`LLMJudge`; a judge → itself; `None` → no judge.

### `parse_json`

```python
parse_json(text: str) -> dict[str, Any]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/judge.py#L163)

Read a judge's reply as JSON (whole text, fenced block or first object), falling back to a `score: N`
pattern.

## `guage_kit.judges.criteria`

The criteria a judge grades against.

A criterion names one quality, says what to look at, and anchors each point of a 1–5 scale in observable
behaviour. Anchored scales make judges agree with people (and with each other) far more than "rate 1 to 10".
Define your own with `Criterion` or in `guage.yaml`.

### `CRITERIA`

```python
CRITERIA = {'correctness': Criterion(name='correctness', question='Is the response factually and substantively correct, judged against the reference answer?', levels={5: 'Fully correct: every claim agrees with the reference; nothing important is missing.', 4: 'Correct in substance with a minor omission or impr …
```

### `Criterion`

*Pydantic model* [source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/criteria.py#L15)

A grading criterion: the question a judge answers, what each score level looks like (anchors), the
scale, and whether the judge sees the reference answer or the retrieved contexts.

| field | type | default |
| --- | --- | --- |
| `name` | `str` | required |
| `question` | `str` | required |
| `levels` | `dict` | `{}` |
| `uses_reference` | `bool` | `False` |
| `uses_contexts` | `bool` | `False` |
| `scale` | `int` | `5` |

- **`Criterion.rubric() -> str`**

### `get_criterion`

```python
get_criterion(spec: str | dict[str, Any] | Criterion) -> Criterion
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/criteria.py#L169)

Resolve a criterion from a built-in name (`correctness`, `groundedness` …), a mapping
(`{name, question, levels}`) or a `Criterion`.

## `guage_kit.judges.calibration`

Can you trust the judge? Agreement between a judge and human labels, and between judges.

Before a judge gates a release, grade a labelled sample and check agreement here (`guage judge calibrate`):
quadratic-weighted kappa and Spearman correlation for graded scores, exact and within-one agreement, mean absolute
error and the judge's systematic bias (does it grade more leniently than people?). Ananke's
`judge_human_agreement` is reported alongside for continuity with Ananke evidence.

### `agreement`

```python
agreement(judge: list[float], human: list[float]) -> dict[str, Any]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/calibration.py#L40)

Agreement statistics between judge scores and human scores on the same scale.

### `position_consistency`

```python
position_consistency(verdicts: list[Any]) -> float | None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/calibration.py#L76)

Share of pairwise verdicts that held when the two responses swapped places (1 means no position bias).

### `weighted_kappa`

```python
weighted_kappa(a: list[int], b: list[int], *, weights: str = 'quadratic') -> float | None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/calibration.py#L14)

Cohen's weighted kappa between two raters' integer grades (`quadratic` or `linear` weights):
agreement beyond chance, where near misses count partly. None when the lists are empty or differ in length.

## `guage_kit.judges.providers`

Model providers for judges and targets.

A provider turns a system prompt and a user prompt into text. Spec strings pick one:

==========================================  ======================================================================
`anthropic:<model>`                       Claude through the official `anthropic` SDK (`guage-kit[anthropic]`)
`openai:<model>`                          OpenAI's chat completions API (`OPENAI_API_KEY`), over plain HTTP
`ollama:<model>`                          a local Ollama server (OpenAI-compatible endpoint on port 11434)
`openai-compatible:<base-url>#<model>`    any OpenAI-compatible server: vLLM, LM Studio, llama.cpp, gateways
`bedrock:<model-id>`                      Amazon Bedrock's Converse API (`guage-kit[bedrock]`)
`python:<module>:<function>`              your own function `fn(system, prompt) -> str`
==========================================  ======================================================================

Keys come from the environment (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GUAGE_OPENAI_COMPATIBLE_KEY`),
never from configuration files.

### `DEFAULT_ANTHROPIC_MODEL`

```python
DEFAULT_ANTHROPIC_MODEL = 'claude-opus-5-5'
```

### `AnthropicProvider`

```python
class AnthropicProvider(
    model: str = 'claude-opus-5-5',
    *,
    max_tokens: int = 16000,
    effort: str | None = None,
    fallbacks: bool = True,
    client: Any = None,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/providers.py#L57)

Claude via the `anthropic` SDK. Server-side refusal fallbacks are on by default (`fallbacks=False` to
turn them off); structured outputs guarantee a JSON verdict when a schema is given.

- **`AnthropicProvider.complete(
    system: str,
    prompt: str,
    *,
    json_schema: dict[str, Any] | None = None,
) -> Completion`**

### `BedrockProvider`

```python
class BedrockProvider(model: str, *, region: str | None = None, max_tokens: int = 4096) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/providers.py#L201)

A provider for models on Amazon Bedrock through the Converse API (needs the `bedrock` extra).

- **`BedrockProvider.complete(
    system: str,
    prompt: str,
    *,
    json_schema: dict[str, Any] | None = None,
) -> Completion`**

### `CallableProvider`

```python
class CallableProvider(fn: Callable[[str, str], Any], name: str = 'python') -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/providers.py#L241)

Wrap `fn(system, prompt) -> str` (or `-> Completion`) as a provider: your own client, a mock, a cache.

- **`CallableProvider.complete(
    system: str,
    prompt: str,
    *,
    json_schema: dict[str, Any] | None = None,
) -> Completion`**

### `Completion`

```python
class Completion(
    text: str,
    model: str = '',
    input_tokens: int = 0,
    output_tokens: int = 0,
    latency_ms: float = 0.0,
    stop_reason: str = '',
    raw: dict[str, Any] = <factory>,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/providers.py#L33)

Completion(text: 'str', model: 'str' = '', input_tokens: 'int' = 0, output_tokens: 'int' = 0, latency_ms: 'float' = 0.0, stop_reason: 'str' = '', raw: 'dict[str, Any]' = <factory>)


### `OpenAICompatibleProvider`

```python
class OpenAICompatibleProvider(
    model: str,
    *,
    base_url: str = 'https://api.openai.com/v1',
    api_key: str | None = None,
    timeout: float = 120.0,
    name: str | None = None,
    max_tokens: int = 4096,
) -> None
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/providers.py#L137)

A provider for any server that speaks the OpenAI-compatible chat completions API
(hosted services, vLLM, LM Studio, llama.cpp server …). Uses the standard library only.

- **`OpenAICompatibleProvider.complete(
    system: str,
    prompt: str,
    *,
    json_schema: dict[str, Any] | None = None,
) -> Completion`**

### `Provider`

```python
class Provider(*args, **kwargs)
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/providers.py#L44)

The protocol a judge or target provider implements: a `name` and `complete(system, prompt, json_schema=None)`
returning a `Completion`.

- **`Provider.complete(
    system: str,
    prompt: str,
    *,
    json_schema: dict[str, Any] | None = None,
) -> Completion`**

### `import_object`

```python
import_object(path: str) -> Any
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/providers.py#L262)

Import `package.module:attr` (or `package.module.attr`).

### `make_provider`

```python
make_provider(spec: str | Provider, **options: Any) -> Provider
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/judges/providers.py#L280)

Build a provider from a spec string (see the module docs) or return a provider as is.
