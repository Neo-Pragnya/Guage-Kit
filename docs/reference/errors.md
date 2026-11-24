---
title: Error codes
description: Stable error codes, what they mean and what to do.
---

# Error codes

Every error Guage Kit raises on purpose carries a stable code. The CLI prints `error GK-…: message` and a hint, and
exits with status **2**. A blocked quality gate is not an error: it exits with **1**. In Python, catch
`guage_kit.GuageError` and branch on `.code`.

```python
import guage_kit as gk

try:
    gk.evaluate("missing.jsonl", ["token_f1"])
except gk.GuageError as exc:
    print(exc.code, exc.message, exc.hint)
```

| code | meaning | what to do |
| --- | --- | --- |
| `GK-DATA-001` | dataset file not found | Check the path; relative paths in guage.yaml are resolved from the suite's folder. |
| `GK-DATA-002` | unsupported dataset format | Use .jsonl, .json, .yaml/.yml, .csv or .tsv. |
| `GK-DATA-003` | invalid sample in dataset | The message names the record (and line for JSON Lines) and the field. Ids must be unique. |
| `GK-DATA-004` | dataset is empty | The dataset (or the filtered slice) has no samples. |
| `GK-METRIC-001` | unknown metric | The hint suggests the closest name. `guage metrics list` shows every metric. |
| `GK-METRIC-002` | invalid metric parameters | A parameter the metric doesn't have, a non-integer after `@`, two metrics with the same display name, or an unknown judge criterion. |
| `GK-METRIC-003` | metric needs an optional extra that is not installed | Install the extra named in the hint, e.g. `pip install 'guage-kit[embeddings]'`. |
| `GK-TARGET-001` | target could not be imported | `module:function` could not be imported or is not callable. |
| `GK-TARGET-002` | target call failed | Your target raised on a sample. The run continues; the sample is reported with its error and left out of every metric. |
| `GK-JUDGE-001` | judge provider is not configured | A judge metric ran without a judge, a provider spec is incomplete, or its SDK or API key is missing. |
| `GK-JUDGE-002` | judge returned an unparseable verdict | The judge's reply had no parsable verdict. Structured output is requested where the provider supports it. |
| `GK-JUDGE-003` | judge provider call failed | The provider call failed (network, quota) or the model declined to judge (a refusal). |
| `GK-CONFIG-001` | invalid suite configuration | guage.yaml is missing, is not valid YAML, or has an unknown or wrongly typed key; also a malformed `--gate`. |
| `GK-RUN-001` | run not found | No such run id, `latest~N` or `baseline:<name>`. `guage runs` lists saved runs. |
| `GK-RUN-002` | runs cannot be compared | The two runs share no sample ids, or no shared sample has outputs in both runs. |
| `GK-HARNESS-001` | installed Ananke Plexus is outside the supported range | The installed ananke-plexus is outside the supported range. `guage doctor` shows the range. |
| `GK-HARNESS-002` | unknown Ananke evaluator | No Ananke evaluator with that id in the installed harness. |
| `GK-REPORT-001` | report could not be written | The report path is not writable, the profile is unknown, or a comparison report lacks its candidate run. |
