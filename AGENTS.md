# Working in Guage Kit

Instructions for coding assistants and contributors. Read these before changing code.

## Boundaries

- **Ananke Plexus owns the harness.** Canonical eval models (`EvalCase`, `AgentTrace`, `EvalScore`), agent-trace
  evaluators, the gate policy engine and evidence bundles live in Ananke. Guage Kit reaches them only through
  `guage_kit.harness` (negotiation, catalogue, conversions) and never re-implements them.
- **Guage Kit owns the evaluation product.** The metric library, judges, statistics, the runner, reports, CLI and
  pytest plugin.
- Keep `SUPPORTED_ANANKE` in `src/guage_kit/harness/negotiation.py` and the `ananke-plexus` range in
  `pyproject.toml` identical (a test checks it).
- **No network at import or in reports.** Reports are offline single files; judges and model targets call out only
  when the user configures them.
- **Permissive licences only** at runtime. Add a dependency only after `make licenses` passes, and prefer an extra.
- Never name or compare with other evaluation products in docs, code or commits.

## Rules for code

- A metric is a function with a declaration (`@metric` / `@corpus_metric`). It returns `None` (skip) when its
  inputs are missing, never a misleading 0. Cite the definition in `reference=`.
- When a reference implementation exists (sacreBLEU, rouge-score, scikit-learn, SciPy), add a parity test against it.
- Errors use the stable codes in `guage_kit.errors`; add a code there and in `docs/reference/errors.md` first.
- Untrusted text (model outputs, datasets) is rendered with `textContent` only. `tests/test_reports.py` guards this.
- After changing metrics, run `make docs-metrics` (the catalogue is generated).

## Commands

```bash
make install            # uv sync with dev tools
make verify             # lint, format check, mypy --strict, tests, licences, generated docs
make acceptance         # capability scenarios (dev install)
make acceptance-wheel   # the same against the built wheel (what ships)
make scan               # distribution scan of dist/
uv run guage doctor     # harness check
```

`acceptance/harness.py` and `scripts/scan_dist.py` are byte-identical copies of the shared tools used across the
Neo Pragnya projects. Change them at their source, not here.
