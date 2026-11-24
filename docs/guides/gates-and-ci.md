---
title: Gates and CI
description: Turn metrics into a release decision - gate rules, verdicts decided by Ananke's policy engine, baselines and regression limits, exit codes, and a complete CI workflow.
---

# Gates and CI

A **gate** turns a run into a decision: PASS, WARN, REVIEW or BLOCK. Gates are what make an evaluation part of a
release process rather than a report someone might read.

## Gate rules

```yaml
gates:
  - {metric: faithfulness, min: 0.85}                       # block below 0.85
  - {metric: recall@5, min: 0.8, on_fail: warn}
  - {metric: judge_correctness, min: 0.7, on_fail: review}  # a person decides
  - {metric: latency_p95, max: 1500, on_fail: warn}
  - {metric: token_f1, max_drop: 0.02}                      # versus the baseline
```

| Key | Meaning |
| --- | --- |
| `metric` | a metric's display name (its `as:` name if it has one) |
| `min`, `max` | bounds on the run value (the mean for sample metrics, the corpus value otherwise) |
| `on_fail` | `block` (default), `review` or `warn` |
| `max_drop` | the largest allowed drop versus the baseline (absolute; a "drop" respects the metric's direction) |

From the command line: `--gate "faithfulness>=0.85"`, `--gate "latency_p95<=1500:warn"` (repeatable). In Python:
`evaluate(..., gates=[{"metric": "faithfulness", "min": 0.85}])` or `GateRule` objects.

## Verdicts

The `min`/`max` rules are handed to **Ananke Plexus's policy engine** (`apply_gate_policy`), the same engine that gates
other evidence in an Ananke-governed project. Guage Kit converts each metric summary to an Ananke `EvalScore`, and
each rule to a `GatePolicyRule`. The worst failed rule decides:

| Verdict | When |
| --- | --- |
| `BLOCK` | a rule with `on_fail: block` failed |
| `REVIEW` | a `review` rule failed and nothing blocked |
| `WARN` | a `warn` rule failed and nothing worse |
| `PASS` | every rule held |

Each check is listed with its value and bound, for example `faithfulness: 0.8218 meets ≥ 0.8`, and the policy
engine's evidence lines are kept (`rag.faithfulness=0.333 < minimum=0.8`).

### Missing values

A rule whose metric produced no value (not computed, or skipped on every sample) **never passes silently**. The
verdict is raised to that rule's own level: BLOCK for `block`, REVIEW for `review`, WARN for `warn`. A typo in a metric name
therefore fails the gate instead of quietly passing it.

## Baselines and regression limits

Runs are saved under `.guage/runs/<run_id>/run.json`. Name a run as a baseline, then compare later runs with it:

```bash
guage baseline set latest            # → .guage/baselines/main.json, referenced as baseline:main
guage baseline set <run_id> --name release-0.4
guage run --baseline baseline:main   # or `baseline: baseline:main` in guage.yaml
```

With a baseline, `guage run` compares the new run with it (see [Statistics](statistics.md)), prints what improved
and regressed, and applies every `max_drop` rule. A drop larger than allowed adds a failed check
(`token_f1 dropped 0.05 versus the baseline (allowed 0.02)`) and raises the verdict to the rule's `on_fail` level.
If the baseline can't be loaded, the run records a note and continues.

Commit the baseline file if CI should compare against it, or download it from your last release's artifacts.

Run references accepted everywhere: a run id, `latest`, `latest~1` (the one before), `baseline:<name>`, a run
directory or a `run.json` path.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | success (and the verdict is better than `--fail-on`) |
| 1 | the verdict reached `--fail-on` (default `block`); or `guage compare --fail-on-regression` found a significant regression |
| 2 | usage, data or configuration error, printed with a stable `GK-*` [error code](../reference/errors.md) |

`--fail-on warn` makes warnings fail CI. `--fail-on never` always exits 0 (useful for a report-only job).

## A CI workflow

This GitHub Actions job runs the suite on every pull request, posts the summary on the job page, uploads the
reports, and fails the check when the gate blocks. It was not run while writing these docs. The `guage` commands in
it were.

```yaml
name: evaluation
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install
        run: pip install "guage-kit[anthropic]" -e .   # your package, so the target imports
      - name: Restore the judge cache
        uses: actions/cache@v4
        with:
          path: .guage/cache
          key: guage-judge-${{ hashFiles('data/**', 'guage.yaml') }}
          restore-keys: guage-judge-
      - name: Evaluate
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: guage run --baseline baseline:main --fail-on block
      - name: Summary
        if: always()
        run: cat reports/guage-summary.md >> "$GITHUB_STEP_SUMMARY"
      - name: Upload reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: guage-reports
          path: |
            reports/
            .guage/runs/
```

It assumes a `guage.yaml` whose `reports:` section writes `reports/guage-summary.md`, `reports/guage-report.html`
and `reports/guage-junit.xml` (the `guage init` default), and a committed `.guage/baselines/main.json`. Pin action
versions to commit SHAs in production workflows.

Notes:

- The Markdown summary has the verdict, every metric with its interval, the gate checks and, with a baseline, the
  before/after table. It is written for pull request comments and job summaries.
- `reports/guage-junit.xml` has one test case per gate check and per metric with a threshold, so CI test viewers
  show quality failures as test failures.
- Use `--profile public` for HTML reports that leave your organisation: it removes inputs, outputs and references.
- Caching `.guage/cache` keeps judge costs at zero for unchanged samples.

## Ananke evidence bundles

`guage run --evidence` (or `evidence: true`, or `evaluate(..., evidence=True)`) also writes the run as an Ananke
evidence bundle:

```text
.ananke/evidence/<run_id>/eval/
├── scores.json            one Ananke EvalScore per metric
├── policy-decision.json   the gate decision
├── manifest.json          file hashes
└── reports/
    ├── report.md
    ├── summary.json
    └── junit.xml
```

Ananke Plexus reads these bundles like any other evaluation evidence (`ananke eval report --run <run_id>`), so
quality results sit next to the rest of a change's evidence. See [Ananke integration](../concepts/ananke-integration.md).
