---
title: Licensing
description: Guage Kit's licence, the licence of every dependency and extra, how the build checks them, and how the metrics relate to the work they cite.
---

# Licensing

Guage Kit is released under the **Apache License 2.0**. You can use it in commercial and closed-source work.

## Runtime dependencies

| Package | Licence | Why |
| --- | --- | --- |
| `ananke-plexus` | Apache-2.0 | evaluation model, agent evaluators, gate policy, evidence |
| `pydantic` | MIT | data models |
| `PyYAML` | MIT | `guage.yaml` and YAML datasets |
| `rich` | MIT | terminal output |
| `typer` | MIT | the CLI |

Through Ananke Plexus, the installed tree also includes `httpx` (BSD-3-Clause, used for OpenAI-compatible providers),
`jinja2` (BSD-3-Clause), `networkx` (BSD-3-Clause), `platformdirs` (MIT) and their dependencies. The full tree has 25
distributions. All are permissive except one: `certifi` (CA certificates, used by `httpx`) is MPL-2.0. MPL-2.0 is a
file-level licence, so it covers only changes to certifi's own files, and it is allowed.

**No copyleft licence (GPL, LGPL, AGPL, SSPL, EUPL, OSL, CC-BY-SA) is installed at runtime.**

## Optional extras

| Extra | Package | Licence |
| --- | --- | --- |
| `anthropic` | `anthropic` | Apache-2.0 |
| `embeddings` | `sentence-transformers` (and its model-serving dependencies) | Apache-2.0 |
| `jsonschema` | `jsonschema` | MIT |
| `bedrock` | `boto3` | Apache-2.0 |

Models downloaded by `sentence-transformers` carry their own licences. Check the model card of the model you choose.

## Development only

These are used as **test oracles**: Guage Kit's own implementations are checked against them. They are not
dependencies of the package.

| Package | Licence | Oracle for |
| --- | --- | --- |
| `sacrebleu` | Apache-2.0 | BLEU, chrF, chrF++ |
| `rouge-score` | Apache-2.0 | ROUGE-1/2/L/Lsum |
| `scikit-learn` | BSD-3-Clause | F1, precision, recall, kappa, MCC, nDCG, AUROC |
| `scipy` | BSD-3-Clause | Spearman, Pearson, binomial and Wilcoxon tests |

## How it is checked

```bash
make licenses          # runs scripts/check_licenses.py
```

The script walks the dependency tree of the installed `guage-kit` through package metadata (optionally with
`--extras anthropic,embeddings`), classifies each distribution's declared licence, and fails on any copyleft licence.
It lists weak copyleft (MPL) separately, and with `--strict` it also fails on unrecognised licences. It runs as part of
`make verify`, before every release.

## Metric definitions

Each metric is an independent implementation of a published definition, and its declaration cites the source
(`guage metrics show <name>` and the [metric reference](../reference/metrics.md) list every source): for example Papineni et al. (2002) for BLEU, Lin (2004) for ROUGE,
Popović (2015, 2017) for chrF, Järvelin and Kekäläinen (2002) for nDCG, and Naeini et al. (2015) and Guo et al. (2017)
for calibration error. Faithfulness and answer relevancy follow the definitions of Es et al. (2024), and context
precision and recall are adapted from the same framework, but all are implemented here with Guage Kit's own claim splitting and support function. No
third-party code is vendored. The red-team probes, criteria rubrics, word lists and demo content were written for this
project.
