---
title: Roadmap
description: What Guage Kit does not do yet, and what is planned next.
---

# Roadmap

Guage Kit 0.1.0 is the first release. These are the known gaps and the planned work, roughly in order. None of it is
a promise of dates.

## Next

- **Async and streaming targets.** Targets run in threads today. Native `async` targets and streaming outputs (time
  to first token as a runtime metric) are planned.
- **Multi-turn conversations.** Samples hold one turn. Conversation-level metrics (goal completion across turns,
  consistency, recovery after a misunderstanding) and simulated users are planned.
- **Trace import from the command line.** Ananke already normalises OpenTelemetry-style spans. A `guage` command
  that imports recorded traces (files or an OTLP export) into a dataset is planned, so agents can be evaluated without
  wrapping them in a target.
- **More providers.** Native providers for more hosted model APIs and local runtimes, beyond the current Anthropic,
  OpenAI-compatible, Ollama and Bedrock support. Any OpenAI-compatible server works today.
- **Corpus metrics in paired comparisons.** Corpus metrics (BLEU, F1, latency percentiles) get a difference in a
  comparison but no significance test. A paired bootstrap over resampled sample sets is planned.

## Later

- **Local web interface.** Browse runs, compare any two, and label samples for judge calibration in a local page
  served by `guage`. Today's HTML reports are static, one file per run.
- **Dataset versioning in the Ananke registry.** Publish and pin evaluation datasets (with their fingerprints,
  provenance and sensitivity) through Ananke's registry, so a gate can require a specific dataset version.
- **Human review workflow.** REVIEW verdicts that collect a reviewer's decision as Ananke evidence.
- **Learned detectors as an extra.** Optional model-based toxicity, PII and natural-language-inference checks beside
  the transparent built-in detectors.
- **More languages.** The lexical metrics tokenise any script, but refusal patterns, the toxicity list and the
  red-team probes are English only.

Suggestions and contributions are welcome. See CONTRIBUTING.md in the repository.
