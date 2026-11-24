---
title: CLI reference
description: Every guage command and option, with exit codes.
---

# CLI reference

`guage` (also installed as `guage-kit`, and runnable as `python -m guage_kit`). Every command has `--help`.
Commands that print results accept `--json` for machine-readable output.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | success |
| 1 | `run`: the gate verdict reached `--fail-on`; `compare`: `--fail-on-regression` found a significant regression |
| 2 | usage, data, configuration or harness error, printed as `error GK-…: message` with a hint (see [error codes](errors.md)) |

`guage --version` prints the version.

## guage version

Print the Guage Kit, Ananke Plexus and Python versions. `--json`.

## guage doctor

Check the Ananke Plexus harness (installed version against the supported range, required capabilities), the
optional extras that are installed, and which provider credentials are set (names only, never values). Prints the
metric count. Exits 2 when the harness is incompatible. `--json`.

## guage init [DIRECTORY]

Write a starter `guage.yaml` and `data/sample.jsonl` (twelve sample records) into `DIRECTORY` (default `.`). Never
overwrites existing files.

| Option | Default | |
| --- | --- | --- |
| `--name` | `my-evaluation` | the suite name |

## guage run [SUITE]

Run an evaluation, gate it, compare it with a baseline if one is set, and write reports. With no arguments it runs
`./guage.yaml`. With `--data`, no suite file is read, and flags describe the whole evaluation. Flags given with a suite
override its values.

| Option | Default | |
| --- | --- | --- |
| `--data`, `-d PATH` | | dataset file instead of a suite |
| `--metrics`, `-m LIST` | auto | comma-separated metric names (`token_f1,recall@5`) |
| `--target SPEC` | | `module:function` or a provider spec |
| `--judge SPEC` | | `heuristic`, `anthropic:<model>`, `ollama:<model>`, `openai:<model>`, … |
| `--gate`, `-g RULE` | | `metric>=value` or `metric<=value`, optionally `:warn` or `:review`; repeatable. Replaces the suite's gates |
| `--slice KEY` | | `tags` or a metadata key; repeatable |
| `--html PATH`, `--junit PATH`, `--markdown`/`--md PATH`, `--json-out PATH` | suite's `reports` | report files |
| `--profile` | `private` | `public` removes sample text from the HTML report |
| `--baseline REF` | suite's `baseline` | compare with a run id, path, `latest~1` or `baseline:<name>`, and apply `max_drop` rules |
| `--repeats N` | 1 | run the target N times per sample |
| `--limit N` | | evaluate only the first N samples |
| `--save` / `--no-save` | save | keep the run under `.guage/runs/` |
| `--evidence` | off | also write an Ananke evidence bundle |
| `--fail-on` | `block` | exit 1 at this verdict or worse: `warn`, `review`, `block` or `never` |
| `--json` | | print the run as JSON instead of tables |

## guage report [RUN]

Render the HTML report of a saved run (default `latest`; any [run reference](../guides/gates-and-ci.md#baselines-and-regression-limits)).

| Option | Default | |
| --- | --- | --- |
| `-o`, `--output PATH` | `guage-report.html` | |
| `--profile` | `private` | or `public` |
| `--against REF` | | include a comparison with this run as the baseline |

## guage compare BASELINE [CANDIDATE]

Compare two saved runs (candidate default `latest`) with paired statistics, and print a table of changes with
intervals, Holm-adjusted p-values and directions.

| Option | Default | |
| --- | --- | --- |
| `-o`, `--output PATH` | | write a comparison HTML report |
| `--judge SPEC` | | also judge the two outputs head to head, in both orders |
| `--criterion` | `helpfulness` | criterion for the head-to-head judge |
| `--min-effect X` | 0.0 | ignore changes smaller than X |
| `--fail-on-regression` | off | exit 1 if any metric regressed significantly |
| `--json` | | the comparison as JSON |

## guage runs

List runs saved under `.guage/runs/`, newest first: id, name, time, samples, verdict. `--json`.

## guage baseline set [RUN]

Copy a run (default `latest`) to `.guage/baselines/<name>.json`; refer to it as `baseline:<name>`. `--name`
(default `main`).

## guage baseline show

Print a baseline's metrics and gate. `--name` (default `main`).

## guage metrics list

List every metric: name, family, level, required fields (and whether it needs a judge), description.

| Option | |
| --- | --- |
| `--family`, `-f PREFIX` | only families starting with PREFIX (`rag`, `ananke`, `ananke.trajectory`) |
| `--json` | full declarations |

## guage metrics show NAME

Print one metric's declaration as JSON: family, level, description, required fields, direction, range, determinism,
judge or embedder needs, extra, parameters with defaults, reference and source.

## guage data validate PATH

Load a dataset. Prints the sample count and fingerprint, or exits 2 with the first problem (file and line for JSON
Lines).

## guage data stats PATH

Field coverage, tag counts, output lengths, and the metrics `auto` would choose. `--json`.

## guage data convert SOURCE DEST

Convert between `.jsonl`, `.json`, `.yaml`/`.yml`, `.csv` and `.tsv`, in either direction (nested values are written to
CSV cells as JSON, which the loader reads back). Field aliases are normalised on the way.

## guage data split SOURCE

Split into `<name>.a.jsonl` and `<name>.b.jsonl` next to the source. `--fraction` (0.5, the share in `a`), `--seed` (0).

## guage data sample SOURCE -n N -o DEST

Write a reproducible random sample of N records. `--seed` (0).

## guage judge calibrate DATA

Grade labelled samples with a judge and report agreement with the human grades: quadratic kappa, Spearman, exact and
within-one agreement, MAE and bias.

| Option | Default | |
| --- | --- | --- |
| `--judge SPEC` | `heuristic` | |
| `--criterion` | `correctness` | |
| `--human-field` | `human_score` | metadata key holding the 1–5 human grade |
| `--json` | | |

## guage probe redteam

Write a red-team dataset: direct and indirect prompt injection with canaries, system-prompt and personal-data
extraction, and over-refusal checks. Run it with `guage run --data … --target …`.

| Option | Default | |
| --- | --- | --- |
| `-o PATH` | `redteam.jsonl` | |
| `--system-prompt FILE` | | your system prompt, to test leakage |

## guage probe perturb SOURCE -o DEST

Write perturbed variants of a dataset. `--kinds` (default `typos,lowercase,filler,distractor`; all kinds are listed in
[Robustness](../guides/robustness.md)), `--seed` (0). An unknown kind exits 2 and lists the valid ones.

## guage probe robustness SOURCE --target SPEC

Run a target on the originals and their variants, then print the robustness score (output agreement) and, per
perturbation, agreement and the three largest metric drops. `--kinds`, `--metrics` (comma-separated; default auto),
`--json`.

## guage synth PATHS...

Generate a test set from documents or folders (`.md`, `.txt`, `.rst`, `.html`).

| Option | Default | |
| --- | --- | --- |
| `-o PATH` | `synthetic.jsonl` | |
| `--provider SPEC` | | a model for natural questions; without it, offline cloze questions |
| `--per-chunk N` | 1 | questions per chunk |
| `--corpus PATH` | | also write the chunks (the corpus to index) |

## guage demo

Evaluate the three demo systems offline and write their reports, a Markdown summary and the runs.
`-o`/`--output` (default `guage-demo`), `--profile`.
