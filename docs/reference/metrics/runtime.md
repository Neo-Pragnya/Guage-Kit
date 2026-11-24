---
title: Runtime and cost metrics
description: "Latency, tokens and cost."
---

# Runtime and cost metrics

> [!NOTE]
> Generated from the metric registry and the metric cards (`guage_kit/metrics/cards/`). Every example
> on this page is run by the test suite, so the numbers are what the metric really returns.

Latency, tokens and cost.

| metric | in one line |
| --- | --- |
| [`cost_usd`](#cost_usd) | The cost of producing this sample's output in US dollars, from the reported cost or from token counts and your price table. Lower is better. |
| [`latency_ms`](#latency_ms) | How long the system took to produce this sample's output, in milliseconds. Lower is better. |
| [`latency_p50`](#latency_p50) | The median latency of the run in milliseconds, so half of the requests were faster. Lower is better. |
| [`latency_p95`](#latency_p95) | The tail latency of the run in milliseconds at the k-th percentile (95 by default), so all but the slowest 5 % of requests were at least this fast. Lower is better. |
| [`total_cost_usd`](#total_cost_usd) | The cost of the whole run in US dollars, the sum of every sample's cost that is known. Lower is better. |
| [`total_tokens`](#total_tokens) | The number of tokens used to produce this sample's output, prompt plus completion. Lower is better. |

## cost_usd

*The cost of producing this sample's output in US dollars, from the reported cost or from token counts and your price table. Lower is better.*

**Level:** sample · **Range:** 0 to ∞, lower is better · **Needs:** `usage` · **Deterministic:** yes

**What it measures**

Per-request spend. The run value is the mean cost per sample; use `total_cost_usd` for the cost of the whole run.

**How it is computed**

1. If the sample has no `usage`, it is skipped.
2. If `usage.cost_usd` is set (your target or provider reported it), use it as is.
3. Otherwise, if `prices` has an entry for the sample's `metadata.model`, compute the cost from the token counts:
   prompt tokens × input price + completion tokens × output price, with prices in dollars per **million** tokens.
   Missing token counts are treated as 0.
4. Otherwise the cost is unknown and the sample is skipped. No prices ship with Guage Kit, because they change.

```text
cost_usd = usage.cost_usd                                                        if set
         = (prompt_tokens · price_in + completion_tokens · price_out) / 1 000 000   if prices[metadata.model] = [price_in, price_out]
         = undefined (skipped)                                                    otherwise
```

**Inputs:** `usage` (required): `cost_usd`, or `prompt_tokens` and `completion_tokens` together with `metadata.model`.

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `prices` | `None` | A table from model name to `[input_price, output_price]` in US dollars per million tokens, for example `{"my-model": [0.25, 1.25]}`. Used only when a sample has no `usage.cost_usd`. Default: none. |

**How to read it**

US dollars, lower is better at equal quality. Compare it against quality metrics, not on its own: a cheaper model that fails more often may cost more per successful task. Dividing `total_cost_usd` by the number of successes (`goal_success`) gives cost per solved task.

**Use it when**

- Choosing between models or prompts on cost at a given quality.
- Budget gates on cost per request.

**Pitfalls**

- Prices go stale. Keep the `prices` table with the run configuration and update it when your provider changes prices.
- The price table is keyed by `metadata.model` exactly; a sample whose model name differs (a dated version suffix) is skipped rather than priced.
- Pricing uses `prompt_tokens` and `completion_tokens`. A sample that reports only `total_tokens` cannot be priced (input and output prices differ) and is skipped.
- Cached-input discounts, batch discounts and per-call fees are not modelled; report `usage.cost_usd` yourself when they matter.

**Example** (checked by the test suite against the real metric)

```jsonl
{"output": "ok", "usage": {"prompt_tokens": 1200, "completion_tokens": 350}, "metadata": {"model": "my-model"}}
```

```yaml
metrics:
- name: cost_usd
  params:
    prices:
      my-model:
      - 0.25
      - 1.25
```

Result: **0.0007375**. 1200 × 0.25 / 10⁶ + 350 × 1.25 / 10⁶ = 0.0003 + 0.0004375 dollars.

**Related:** [`total_cost_usd`](#total_cost_usd), [`total_tokens`](#total_tokens), [`ananke.efficiency.cost_budget`](ananke.md#anankeefficiencycost_budget)

## latency_ms

*How long the system took to produce this sample's output, in milliseconds. Lower is better.*

**Level:** sample · **Range:** 0 to ∞, lower is better · **Needs:** `latency_ms` · **Deterministic:** yes

**What it measures**

Per-request response time. Its run value is the **mean** latency, which is useful for throughput and cost planning but hides the slow tail users notice; read it next to `latency_p50` and `latency_p95`.

**How it is computed**

1. Read the sample's `latency_ms` and report it unchanged.
2. When Guage Kit runs your target, it measures the wall-clock time of each call and fills this field; when you
   evaluate a file of recorded outputs, the field comes from the file. Samples without it are skipped.

```text
latency_ms = sample.latency_ms
run value  = mean over samples that have it
```

**Inputs:** `latency_ms` (required, milliseconds).

**How to read it**

Milliseconds, lower is better, no upper bound. Only comparable across runs made on the same hardware, network, region and concurrency. As a rule of thumb for chat interfaces, users notice delays above about one second before the first visible output; for agents, total task time matters more than any one call.

**Use it when**

- Comparing models, prompt lengths or retrieval settings on speed.
- Gating releases on a latency budget per request (use a threshold with the direction lower-is-better).

**Pitfalls**

- The mean is pulled up by a few very slow requests and still hides them. Report percentiles for user-facing latency.
- Measured end to end around your target, so it includes network, queueing, retries and retrieval, not just model time.
- Concurrency changes latency. A run with `concurrency` 16 may show higher per-request latency than a sequential one because of rate limits and queueing.
- Streaming systems care about time to first token, which this field does not capture unless your target records it that way.

**Example** (checked by the test suite against the real metric)

```jsonl
{"output": "ok", "latency_ms": 842.5}
```

Result: **842.5**

**Related:** [`latency_p50`](#latency_p50), [`latency_p95`](#latency_p95), [`total_tokens`](#total_tokens), [`ananke.efficiency.latency`](ananke.md#anankeefficiencylatency), [`ananke.efficiency.wall_clock`](ananke.md#anankeefficiencywall_clock)

## latency_p50

*The median latency of the run in milliseconds, so half of the requests were faster. Lower is better.*

**Level:** corpus · **Range:** 0 to ∞, lower is better · **Needs:** `latency_ms` · **Deterministic:** yes

**What it measures**

Typical response time, robust to a few very slow or very fast outliers. It is a corpus metric: one number for the whole run.

**How it is computed**

1. Collect `latency_ms` from every sample that has it and sort the values.
2. Take the 50th percentile with linear interpolation between the two nearest ranks: position
   h = (n − 1) × 0.5 in the zero-based sorted list. With an even number of samples this is the average of the two
   middle values; with an odd number it is the middle value.

```text
x_(0) ≤ … ≤ x_(n−1)   sorted latencies
h     = (n − 1) · p / 100,  p = 50
Q(p)  = x_(⌊h⌋) + (h − ⌊h⌋) · (x_(⌊h⌋+1) − x_(⌊h⌋))      (Hyndman and Fan definition 7)
```

**Inputs:** `latency_ms` (required) on each sample.

**How to read it**

Milliseconds, lower is better. The latency a typical user sees. If the median is fine but users complain, look at `latency_p95`; if the mean (`latency_ms`) is much higher than the median, a minority of requests is very slow.

**Use it when**

- Summarising the typical speed of a system in one robust number.
- Comparing two versions where a few timeouts would distort the mean.

**Pitfalls**

- Says nothing about the tail. A system with p50 of 300 ms can still time out for 5 % of users.
- Small runs give unstable percentiles; with 10 samples the median moves with any one of the middle values.
- Only comparable across runs made under the same conditions (hardware, region, concurrency).

**Example** (checked by the test suite against the real metric)

```jsonl
{"output": "ok", "latency_ms": 120}
{"output": "ok", "latency_ms": 180}
{"output": "ok", "latency_ms": 200}
{"output": "ok", "latency_ms": 240}
{"output": "ok", "latency_ms": 260}
{"output": "ok", "latency_ms": 300}
{"output": "ok", "latency_ms": 350}
{"output": "ok", "latency_ms": 400}
{"output": "ok", "latency_ms": 900}
{"output": "ok", "latency_ms": 2400}
```

Result: **280**. Ten samples, so the median is halfway between the 5th and 6th sorted values (260 and 300). The mean of the same run is 535 ms, pulled up by the 2400 ms request.

**Related:** [`latency_p95`](#latency_p95), [`latency_ms`](#latency_ms)

**References**

- Hyndman, R. J., and Fan, Y. (1996). Sample Quantiles in Statistical Packages. The American Statistician, 50(4), 361–365. <https://doi.org/10.1080/00031305.1996.10473566>

## latency_p95

*The tail latency of the run in milliseconds at the k-th percentile (95 by default), so all but the slowest 5 % of requests were at least this fast. Lower is better.*

**Level:** corpus · **Range:** 0 to ∞, lower is better · **Needs:** `latency_ms` · **Deterministic:** yes

**What it measures**

How slow the slow requests are: the experience of the unluckiest users and the number latency budgets and service-level objectives are usually written against. It is a corpus metric.

**How it is computed**

1. Collect `latency_ms` from every sample that has it and sort the values.
2. Take the k-th percentile with linear interpolation between the two nearest ranks, at zero-based position
   h = (n − 1) × k / 100 (the same rule as `latency_p50`).
3. Details report the percentile used and the maximum latency in the run.
`latency_p95@99` sets k = 99 for the p99.

```text
x_(0) ≤ … ≤ x_(n−1)   sorted latencies
h     = (n − 1) · k / 100
Q(k)  = x_(⌊h⌋) + (h − ⌊h⌋) · (x_(⌊h⌋+1) − x_(⌊h⌋))      (Hyndman and Fan definition 7)
```

**Inputs:** `latency_ms` (required) on each sample.

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `k` | `95` | The percentile, from 0 to 100 (default 95). Use 99 for the p99 (`latency_p95@99`), 90 for a looser tail. |

**How to read it**

Milliseconds, lower is better. Gate on it with a maximum (for example p95 under 2000 ms). A large gap between p50 and p95 means inconsistent performance: cold starts, long inputs, retries or rate limiting. Compare it with the `max` in details to see whether one outlier dominates.

**Use it when**

- Latency budgets and service-level objectives.
- Detecting regressions that affect only some requests (long documents, particular tools).

**Pitfalls**

- Needs enough samples to mean anything. With 10 samples the p95 is an interpolation between the two slowest requests, and the p99 is nearly the maximum; aim for hundreds of samples before trusting p99.
- Linear interpolation means the value need not be a latency that any request actually had.
- Only comparable across runs made under the same conditions (hardware, region, concurrency).

**Example** (checked by the test suite against the real metric)

```jsonl
{"output": "ok", "latency_ms": 120}
{"output": "ok", "latency_ms": 180}
{"output": "ok", "latency_ms": 200}
{"output": "ok", "latency_ms": 240}
{"output": "ok", "latency_ms": 260}
{"output": "ok", "latency_ms": 300}
{"output": "ok", "latency_ms": 350}
{"output": "ok", "latency_ms": 400}
{"output": "ok", "latency_ms": 900}
{"output": "ok", "latency_ms": 2400}
```

```yaml
metrics:
- name: latency_p95
  params:
    k: 95
```

Result: **1725**. h = 9 × 0.95 = 8.55, so the value is 55 % of the way from 900 to 2400 ms. With `k: 99` the same run gives 2265 ms.

**Related:** [`latency_p50`](#latency_p50), [`latency_ms`](#latency_ms), [`ananke.efficiency.latency`](ananke.md#anankeefficiencylatency)

**References**

- Hyndman, R. J., and Fan, Y. (1996). Sample Quantiles in Statistical Packages. The American Statistician, 50(4), 361–365. <https://doi.org/10.1080/00031305.1996.10473566>

## total_cost_usd

*The cost of the whole run in US dollars, the sum of every sample's cost that is known. Lower is better.*

**Level:** corpus · **Range:** 0 to ∞, lower is better · **Needs:** `usage` · **Deterministic:** yes

**What it measures**

Total spend for an evaluation run or a batch of traffic. It is a corpus metric: one number, the sum rather than the mean.

**How it is computed**

1. Keep the samples that have `usage`.
2. For each, compute its cost exactly as `cost_usd` does: `usage.cost_usd` if reported, otherwise token counts
   times `prices[metadata.model]` (dollars per million tokens).
3. Sum the costs that are known. Samples whose cost cannot be determined are left out of the sum.
4. If no sample has a known cost, the value is undefined.

```text
total_cost_usd = Σ_{s with a known cost} cost_usd(s)
```

**Inputs:** `usage` (required) on each sample; `metadata.model` when pricing from tokens.

**Parameters**

| parameter | default | meaning |
| --- | --- | --- |
| `prices` | `None` | A table from model name to `[input_price, output_price]` in US dollars per million tokens, for example `{"my-model": [0.25, 1.25]}`. Used only for samples without `usage.cost_usd`. Default: none. |

**How to read it**

US dollars, lower is better. Scales with dataset size, so compare runs over the same samples, or divide by the sample count (`n` in details is the number of samples with usage) for a per-sample figure.

**Use it when**

- Reporting what an evaluation run or a batch job cost.
- Gating on a budget for a fixed benchmark.

**Pitfalls**

- Samples with unknown cost are skipped silently, so the total is a lower bound. Check that every sample reports `usage.cost_usd` or has a priced `metadata.model`.
- Inherits the `cost_usd` caveats (stale prices, exact model-name lookup, samples with only `total_tokens` skipped).
- Does not include the cost of judge calls made during evaluation, only the target's own usage.

**Example** (checked by the test suite against the real metric)

```jsonl
{"output": "a", "usage": {"cost_usd": 0.0021}}
{"output": "b", "usage": {"prompt_tokens": 1200, "completion_tokens": 350}, "metadata": {"model": "my-model"}}
{"output": "c", "usage": {"prompt_tokens": 800}}
```

```yaml
metrics:
- name: total_cost_usd
  params:
    prices:
      my-model:
      - 0.25
      - 1.25
```

Result: **0.0028375**. 0.0021 reported + 0.0007375 priced from tokens. The third sample has no cost and no model, so it is left out of the sum.

**Related:** [`cost_usd`](#cost_usd), [`total_tokens`](#total_tokens), [`ananke.efficiency.cost_budget`](ananke.md#anankeefficiencycost_budget)

## total_tokens

*The number of tokens used to produce this sample's output, prompt plus completion. Lower is better.*

**Level:** sample · **Range:** 0 to ∞, lower is better · **Needs:** `usage` · **Deterministic:** yes

**What it measures**

Per-request token consumption, the main driver of cost and a large part of latency. "Total" means prompt plus completion for one sample; the run value is the **mean** per sample, not the sum over the run.

**How it is computed**

1. Read the sample's `usage`.
2. Use `usage.total_tokens` when it is set.
3. Otherwise add `prompt_tokens` and `completion_tokens`, treating a missing one as 0.
4. If none of the three is set (or there is no `usage`), the sample is skipped.

```text
total_tokens = usage.total_tokens                                  if set
             = (usage.prompt_tokens or 0) + (usage.completion_tokens or 0)   otherwise
```

**Inputs:** `usage` (required): `total_tokens`, or `prompt_tokens` and `completion_tokens`, as reported by the model provider.

**How to read it**

Tokens, lower is better for the same quality. Multiply the run's mean by the number of samples for the run total. A jump after a change usually means a longer prompt (more retrieved context, a longer system prompt) or more verbose answers; check which by looking at prompt and completion tokens separately.

**Use it when**

- Watching prompt growth from retrieval or few-shot examples.
- Comparing verbosity of models or prompts at equal quality.

**Pitfalls**

- Token counts depend on the tokenizer, so they are not comparable across model families.
- Only as complete as your target reports. Agent runs with several model calls must sum them into `usage` themselves.
- Prompt and completion tokens are usually priced differently; use `cost_usd` for money.

**Example** (checked by the test suite against the real metric)

```jsonl
{"output": "ok", "usage": {"prompt_tokens": 1200, "completion_tokens": 350}}
```

Result: **1550**

**Related:** [`cost_usd`](#cost_usd), [`total_cost_usd`](#total_cost_usd), [`ananke.efficiency.token_budget`](ananke.md#anankeefficiencytoken_budget), [`ananke.efficiency.cache_efficiency`](ananke.md#anankeefficiencycache_efficiency)
