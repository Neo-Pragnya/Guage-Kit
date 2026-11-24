---
title: Robustness
description: Perturb inputs and retrieved contexts, run the system on every variant, and measure how often its answer holds and how much each metric drops.
---

# Robustness

A system that answers "What is the refund window?" correctly but fails on "what is the refnud window" is fragile.
Robustness probes make controlled variants of each input and measure the effect.

## Perturbations

| Kind | Changes |
| --- | --- |
| `typos` | swaps, drops or keyboard-neighbour substitutions in about 6% of letters |
| `uppercase`, `lowercase` | the whole input |
| `no_punctuation` | removes punctuation |
| `whitespace` | doubles the spaces between words, adds trailing whitespace |
| `filler` | a chatty prefix ("Quick question: …") |
| `distractor` | an irrelevant sentence at the end |
| `shuffle_contexts` | reorders the retrieved contexts |
| `drop_top_context` | removes the first context |
| `noise_context` | inserts an unrelated passage among the contexts |

Text perturbations apply to string inputs. Context perturbations need at least one context (shuffle and drop need
two). A variant's id is `<id>~<kind>`, its output is cleared, and `metadata.perturbation` and `original_id` record
where it came from. Perturbations are seeded and reproducible.

## Running a robustness check

```bash
guage probe robustness data/qa.jsonl --target my_package.pipeline:answer --kinds typos,lowercase,filler,distractor
```

```python
from guage_kit.probes import robustness
from guage_kit import load_dataset

res = robustness(load_dataset("data/qa.jsonl"), "my_package.pipeline:answer",
                 kinds=["typos", "filler", "noise_context"], metrics=["token_f1", "faithfulness"])
res["robustness_score"]            # mean output agreement over every variant
res["perturbations"]["typos"]      # {"n", "output_agreement", "metric_delta": {metric: mean change}}
res["runs"]["original"], res["runs"]["perturbed"]   # the two full runs, for reports
```

`robustness` evaluates the originals, then the variants, and pairs each variant with its original:

- **output agreement**: token F1 between the original answer and the variant's answer (1 when they are the same
  after normalisation). It needs no ground truth.
- **metric delta**: the mean change in each metric (variant minus original). A negative delta for `typos` means
  spelling mistakes cost quality.

## Variants as a dataset

To keep variants under version control, or to run them through a normal suite:

```bash
guage probe perturb data/qa.jsonl -o data/qa-perturbed.jsonl --kinds typos,noise_context --seed 0
```

Each variant is tagged `perturbation:<kind>`, so `slices: [tags]` breaks the results down by perturbation.

## Reading the numbers

- Agreement near 1 on `lowercase`, `whitespace` and `filler` is expected of any production system. Drops there
  usually point to brittle prompt templates or exact-match routing.
- `typos` and `distractor` are harder, so compare them between versions rather than against an absolute bar.
- For RAG, a large `faithfulness` drop under `noise_context` means the generator uses whatever it is given. A
  drop under `drop_top_context` shows how much the system depends on a perfect first hit.
- `repeats` (see [Targets](targets.md)) measures the separate question of stability on the *same* input.
