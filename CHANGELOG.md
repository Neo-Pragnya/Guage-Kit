# Changelog

All notable changes are recorded here. The project follows [semantic versioning](https://semver.org/).

## [Unreleased]

## [0.1.1] - 2026-11-24

### Added
- **Metric cards** for all 90 native metrics (`guage_kit/metrics/cards/`): what each measures, how it is computed
  (with the formula), its parameters, how to read it, when to use it, pitfalls, a worked example and the papers that
  define it. Every example is run by the test suite, so the documented numbers are what the metric returns.
- **Evaluator cards** for all 77 Ananke Plexus evaluators, written from their source: what each reads from the trace,
  when it passes and what its arguments mean.
- `guage metrics show <name>` prints the card (`--json` for the declaration plus the card).
- **Metric reference**: one page per family plus the Ananke evaluators, generated from the cards.
- **API reference** generated from the code: every public class and function, judge criteria with their anchors,
  perturbations, statistical methods with their papers, and every CLI option. `make docs-generate` regenerates it;
  CI fails when it is stale.
- Website: an animated terminal on the homepage (also in the README), and the release version in the header and the
  docs sidebar.

### Fixed
- chrF ignores all whitespace (newlines and tabs included) and chrF++ separates leading punctuation, as sacreBLEU
  does; corpus chrF uses each sample's best reference.
- A line break always ends a sentence, so rougeLsum matches rouge-score on one-sentence-per-line text.
- Numbers like "1,2,3" are three numbers, not 123 (thousands separators need groups of three).
- Grouped citations such as `[1, 2]` count for citation coverage and accuracy.
- Refusal detection handles typographic apostrophes (I’m, can’t).
- `pii_leakage` compares full values when ignoring personal data echoed from the input (it compared masked values).
- `cost_usd` skips samples that report only total tokens instead of pricing them at 0.
- `precision`, `hit_rate` and `mrr` skip samples without relevant ids, like the other ranking metrics;
  `context_relevance` skips questions without content words instead of scoring 0.
- `latency_p95@k` rejects a percentile outside 0–100 with a clean error.
- Declarations: Brier's range is 0–2 (multi-class form); alignment, uniformity and anisotropy declare that they use
  an embedder; RAG metric references credit the right papers.
- The README renders fully on PyPI: links are absolute, and the Python-versions badge is static (the dynamic one
  often failed to load). A test keeps it that way.
- Tests read and write files as UTF-8, so the suite passes on Windows.

### Changed
- Coverage is measured from interpreter start (`coverage run -m pytest`), because the pytest plugin entry point
  imports the package before pytest-cov starts. Added tests for the CLI and the built-in JSON Schema validator
  (160 tests, 87% coverage).
- First release published by the release pipeline rather than from a workstation.

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
