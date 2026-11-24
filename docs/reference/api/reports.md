---
title: "Reports"
description: "The offline HTML report, Markdown summaries, JUnit XML and the report view model."
---

# Reports

> [!NOTE]
> Generated from the code by `scripts/gen_api_docs.py`; signatures and docstrings are the installed
> package's.

Reports are single self-contained files; see the [report format](../report-format.md) for the manifest and the view model's schema.

## `guage_kit.reports`

Reports: one offline HTML file per run or comparison, plus Markdown (PR comments, CI summaries), JUnit XML
(CI test views) and JSON.

### `junit`

```python
junit(run: RunResult) -> str
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/reports/__init__.py#L72)

JUnit XML: one test case per gate check (or per thresholded metric), so CI shows quality as tests.

### `markdown`

```python
markdown(run: RunResult, comparison: Any = None, *, max_rows: int = 40) -> str
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/reports/__init__.py#L25)

A compact Markdown summary for a pull request comment or `$GITHUB_STEP_SUMMARY`.

### `render_html`

```python
render_html(model: dict[str, Any]) -> str
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/reports/html.py#L160)

Render a view model into one self-contained, offline HTML page (inline assets, a strict
Content-Security-Policy and an embedded manifest).

### `view_model`

```python
view_model(
    run: RunResult,
    *,
    comparison: Any = None,
    profile: str = 'private',
    title: str | None = None,
) -> dict[str, Any]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/reports/html.py#L61)

The data a report renders, as plain JSON: run summary, metrics, slices, samples, comparison and
environment. The `public` profile removes sample text.

### `write_all`

```python
write_all(
    run: RunResult,
    out_dir: str | Path,
    *,
    comparison: Any = None,
    profile: str = 'private',
) -> dict[str, Path]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/reports/__init__.py#L109)

Write every report for a run into a folder: `report.html`, `summary.md`, `junit.xml` and
`run.json`. Returns their paths by kind.

### `write_report`

```python
write_report(
    result: Any,
    path: str | Path,
    *,
    comparison: Any = None,
    profile: str = 'private',
    title: str | None = None,
    run_b: RunResult | None = None,
) -> Path
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/reports/html.py#L198)

Write the HTML report. `result` is a run; pass `comparison` (and the candidate as the run) for a
before/after report, or a `guage_kit.runner.compare.Comparison` together with `run_b`.

## `guage_kit.reports.html`

Render a run (and optionally a comparison) into one self-contained, offline HTML file.

Guarantees (tests/test_reports.py):

- **Offline.** CSS and JavaScript are inlined. No CDN, font, image or telemetry URL is referenced, and the page's
  Content Security Policy is `default-src 'none'` with the inline script and style allowed only by their sha256
  hashes, so nothing can load or connect even if injected.
- **Safe.** Data is embedded as JSON in `<script type="application/json">` with `<`, `>`, `&` and the
  U+2028/U+2029 separators escaped, so evaluated text (model outputs can be hostile) can never close the script.
  The page sets every piece of untrusted text with `textContent`.
- **Shareable.** The `public` profile removes inputs, outputs, references, contexts and the git revision,
  keeping only scores. The manifest records which profile was used.
- **Traceable.** A manifest (renderer, versions, input digest, dataset fingerprint) is embedded in the page.

### `RENDERER`

```python
RENDERER = 'guage-kit/report-html@1'
```

### `render_html`

```python
render_html(model: dict[str, Any]) -> str
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/reports/html.py#L160)

Render a view model into one self-contained, offline HTML page (inline assets, a strict
Content-Security-Policy and an embedded manifest).

### `safe_json`

```python
safe_json(data: Any) -> str
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/reports/html.py#L37)

JSON that is safe inside an HTML `<script>` element.

### `view_model`

```python
view_model(
    run: RunResult,
    *,
    comparison: Any = None,
    profile: str = 'private',
    title: str | None = None,
) -> dict[str, Any]
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/reports/html.py#L61)

The data a report renders, as plain JSON: run summary, metrics, slices, samples, comparison and
environment. The `public` profile removes sample text.

### `write_report`

```python
write_report(
    result: Any,
    path: str | Path,
    *,
    comparison: Any = None,
    profile: str = 'private',
    title: str | None = None,
    run_b: RunResult | None = None,
) -> Path
```

[source](https://github.com/Neo-Pragnya/Guage-Kit/blob/main/src/guage_kit/reports/html.py#L198)

Write the HTML report. `result` is a run; pass `comparison` (and the candidate as the run) for a
before/after report, or a `guage_kit.runner.compare.Comparison` together with `run_b`.
