---
title: "Perturbations"
description: "Every input and context perturbation used by robustness runs."
---

# Perturbations

> [!NOTE]
> Generated from `guage_kit/probes`.

A robustness run (`guage probe robustness`) evaluates a target on the original samples and on perturbed copies,
then reports how often the output stays the same and how much each metric drops. Perturbations are seeded,
so a run is reproducible. See the [robustness guide](../../guides/robustness.md).

| kind | what it changes |
| --- | --- |
| `typos` | Introduces typing errors in about 6% of the input's letters: swapped neighbours, dropped letters and neighbouring-key substitutions. |
| `uppercase` | Turns the whole input into capitals. |
| `lowercase` | Turns the whole input into lower case. |
| `no_punctuation` | Removes every punctuation character from the input. |
| `whitespace` | Doubles the spaces between words and adds trailing whitespace or a newline. |
| `filler` | Prepends a conversational opener ("Quick question: ", "Hi! I was wondering, " …). |
| `distractor` | Appends an irrelevant sentence ("By the way, I like turtles."). |
| `shuffle_contexts` | Reorders the retrieved contexts (needs at least two): the answer should not depend on order. |
| `drop_top_context` | Removes the first retrieved context (needs at least two): how much does the answer rely on it? |
| `noise_context` | Inserts an unrelated passage at a random position among the contexts. |

## Background

- Ribeiro, M. T., Wu, T., Guestrin, C. and Singh, S. (2020). Beyond Accuracy: Behavioral Testing of NLP Models with CheckList. ACL 2020. [ACL Anthology](https://aclanthology.org/2020.acl-main.442/)
- Shi, F. et al. (2023). Large Language Models Can Be Easily Distracted by Irrelevant Context. ICML 2023. [arXiv:2302.00093](https://arxiv.org/abs/2302.00093)
- Liu, N. F. et al. (2024). Lost in the Middle: How Language Models Use Long Contexts. TACL 12. [ACL Anthology](https://aclanthology.org/2024.tacl-1.9/)
