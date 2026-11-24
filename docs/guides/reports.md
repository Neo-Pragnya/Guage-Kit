---
title: Reports
description: The offline HTML report and its views, comparison reports, public and private profiles, and the Markdown, JUnit and JSON outputs.
---

# Reports

Every run can be written as:

| Format | Use | How |
| --- | --- | --- |
| HTML | read, explore and share one run or a before/after comparison | `reports.html` in `guage.yaml`, `--html`, `guage report`, `gk.report(run, path)` |
| Markdown | pull request comments, CI job summaries | `reports.markdown`, `--markdown`, `guage_kit.reports.markdown(run, comparison)` |
| JUnit XML | CI test views: one test case per gate check and per thresholded metric | `reports.junit`, `--junit`, `guage_kit.reports.junit(run)` |
| JSON | the complete run (`run.json`) for tooling and later comparisons | `reports.json`, `--json-out`, `run.save(path)` |

`guage_kit.reports.write_all(run, out_dir, comparison=None, profile="private")` writes all four into one folder.

## The HTML report

One self-contained file, with no network access and nothing to install (see [Report safety](../concepts/report-safety.md)).
It follows the system's light or dark setting, has a theme toggle, and works on a phone.

| View | Shows |
| --- | --- |
| **Overview** | the gate verdict with icon and label; dataset, target, judge, timing; one tile per metric with its value, 95% interval, a dot-and-interval bar (dashed line at the threshold), the sample distribution and whether it meets its threshold; the gate checks; run notes. Click a tile to open the metric |
| **Metrics** | a sortable table (value, interval, n, skipped, threshold, pass rate) and a detail panel for the selected metric: histogram, statistics, the confusion matrix and per-label table for classification, the reliability diagram for calibration, other details, and the weakest samples |
| **Slices** | a heatmap of every slice (tag or metadata value) against every metric. Each column is shaded from its weakest slice to its strongest, lower-is-better metrics are flipped, every cell prints its value, and hovering shows the interval and n |
| **Samples** | every sample with search, tag filter, "failing a threshold only", and sorting by the weakest score on any metric. A sample opens to its input, output, reference, repeated outputs, tags and every score with its explanation; faithfulness shows its claim table with each claim marked supported or not |
| **Comparison** | only with a comparison: see below |
| **About** | the manifest, environment (versions, git revision), dataset fingerprints, judge usage and the full configuration |

Charts have tooltips (also reachable by keyboard), and tabs switch with the arrow keys.

## Comparison reports

```bash
guage compare baseline:main latest -o comparison.html
guage report latest --against baseline:main -o comparison.html
```

```python
from guage_kit.runner import compare
gk.report(candidate_run, "comparison.html", comparison=compare(baseline_run, candidate_run))
```

The comparison view shows:

- a forest plot: each metric's mean change with its 95% paired interval, coloured by direction (blue improved, red
  regressed, gray not significant) and labelled. Only metrics on a 0–1 scale share the plot's axis; metrics on other
  scales (latency, tokens, cost) are listed beneath it and appear in the table;
- a table with before, after, change, interval, Holm-adjusted p, effect size and wins/losses/ties;
- the head-to-head judge result, if you ran one;
- the samples that regressed and improved most, with both outputs side by side.

The rest of the report describes the candidate run.

## Profiles

| | `private` (default) | `public` |
| --- | --- | --- |
| metric summaries, intervals, slices, gate | yes | yes |
| per-sample scores | yes | yes |
| inputs, outputs, references, repeated outputs | yes | removed |
| score explanations and details (claims, reasons) | yes | removed |
| comparison sample text and head-to-head rows | yes | removed |
| dataset source path, git revision | yes | removed |

Use `--profile public` (or `reports.profile: public`) before sharing a report outside the people who may see the
data. The report lists what was removed among its limitations, and the manifest records the profile.

## Re-rendering a saved run

```bash
guage runs                                   # saved runs, newest first
guage report latest -o report.html
guage report <run_id> -o report.html --profile public
```

Text fields longer than 6,000 characters are shortened in the HTML (the full text stays in `run.json`).
