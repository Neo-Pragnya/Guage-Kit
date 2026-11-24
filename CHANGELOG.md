# Changelog

All notable changes are recorded here. The project follows [semantic versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-24

First public release: a complete rewrite of the earlier prototype, rebuilt on Ananke Plexus.

### Added
- **Evaluation engine** (`guage_kit.evaluate`): datasets from JSON Lines, JSON, YAML, CSV or TSV with field aliases;
  optional target (your function, `module:function` or a model) with concurrency, retries and repeats
  (`self_consistency`); automatic metric selection from the fields present; bootstrap confidence intervals for
  sample and corpus metrics; slices by tag or metadata; reproducible run files with dataset fingerprints, versions
  and git revision.
- **90 native metrics** across text, semantic similarity, RAG, retrieval, classification, calibration, embeddings,
  structured output, safety, agents, runtime and judges. BLEU, chrF and ROUGE match sacreBLEU and rouge-score;
  retrieval and classification metrics match scikit-learn (tested).
- **77 Ananke Plexus evaluators** discovered from the installed harness and exposed as `ananke.*` metrics, with
  arguments resolved from parameters, `metadata.ananke` or expected tool calls.
- **Judges**: 11 anchored criteria and custom rubrics; Claude through the official SDK (structured verdicts,
  server-side refusal fallbacks), OpenAI-compatible servers, Ollama, Amazon Bedrock and any function; on-disk cache,
  self-consistency, pairwise comparison with order swapping, an offline heuristic judge, and agreement statistics
  against human labels.
- **Comparisons**: paired bootstrap intervals, permutation and sign tests, Holm correction, effect sizes, sample
  regressions; pairwise judging of two runs; named baselines and `max_drop` regression gates.
- **Gates** decided by Ananke's policy engine (PASS / WARN / REVIEW / BLOCK), exit codes and `--fail-on`;
  Ananke evidence bundles.
- **Reports**: an offline single-file HTML report (overview, metrics, slices heatmap, samples with explanations,
  comparison forest plot) with a hash-locked Content Security Policy and a public profile; Markdown, JUnit XML, JSON.
- **CLI** `guage`: init, run, report, compare, runs, baseline, metrics, data, judge calibrate, probe, synth, demo,
  doctor, version.
- **pytest plugin** with the `guage` fixture, `--guage-report` and `--guage-junit`.
- **Probes**: perturbation robustness and a red-team set (direct and indirect prompt injection with canaries, system
  prompt and personal-data extraction, over-refusal).
- **Synthetic data**: chunking, offline cloze questions, model-generated grounded questions.
- Documentation site, acceptance suite and release gate, distribution scan, licence check.

### Removed
- The Streamlit interface, the old adapters and notebooks of the prototype. HTML reports replace the interface.
