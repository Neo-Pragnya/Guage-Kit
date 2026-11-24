---
title: pytest
description: Write evaluations as tests with the guage fixture, check quality bars, and collect HTML reports and JUnit files from a test session.
---

# pytest

Installing Guage Kit registers a pytest plugin (entry point `pytest11`), so evaluations can live in your test suite
and run wherever your tests run. The plugin imports nothing heavy until a test uses it.

## The `guage` fixture

```python
import guage_kit as gk


def test_support_answers(guage):
    data = [gk.Sample(id="1", input="Capital of France?", output="Paris.", expected="Paris"),
            gk.Sample(id="2", input="Largest ocean?", output="The Pacific.", expected="Pacific")]
    run = guage.evaluate(data, ["contains", "token_f1"])
    guage.check(run, contains=1.0, token_f1=0.5)


def test_one_answer(guage):
    guage.assert_metric("faithfulness", "Water boils at 100 degrees Celsius.",
                        contexts=["At sea level water boils at 100 degrees Celsius."], minimum=0.8)


def test_latency_bar(guage):
    data = [gk.Sample(id="1", output="ok", latency_ms=420.0), gk.Sample(id="2", output="ok", latency_ms=610.0)]
    run = guage.evaluate(data, ["latency_p95"])
    guage.check(run, latency_p95=("<=", 800))
```

```bash
pytest --guage-report=reports
```

```text
...                                                                      [100%]
================================== Guage Kit ===================================
test_quality.py::test_support_answers: – · contains=1.000, token_f1=1.000
test_quality.py::test_latency_bar: – · latency_p95=600.500
report: reports/00-test-support-answers.html
report: reports/01-test-latency-bar.html
3 passed
```

| Method | Does |
| --- | --- |
| `guage.evaluate(...)` | the same arguments as `guage_kit.evaluate`; the run is named after the test and recorded for the session summary and reports. A `target=` runs your system live |
| `guage.check(run, metric=minimum, other=("<=", maximum))` | fails the test, listing every missed bar (`token_f1 = 0.42, expected >= 0.5`), a metric without value, or a gate that blocked. For a name with `@`, write `__at__`: `recall__at__5=0.8` |
| `guage.assert_metric(metric, output, expected=None, *, minimum=None, maximum=None, **fields)` | scores one output and fails with the value and the output when it misses. `fields` are other sample fields (`contexts`, `input`, `tool_calls`, …), plus `params={...}` and `judge="heuristic"` |
| `guage.score(metric, output, expected=None, **fields)` | the value only (`None` when the metric can't apply) |

`assert_metric` and `score` use the offline hashing embedder. With `judge=` they accept any judge spec.

## Options

| Option | Effect |
| --- | --- |
| `--guage-report=DIR` | write an HTML report for every run recorded in the session |
| `--guage-junit=DIR` | write a JUnit XML file per recorded run (in addition to pytest's own JUnit output) |

The terminal summary always lists the recorded runs with their verdict and first metrics.

## Tips

- Keep a small, fast offline set in the unit-test run (recorded outputs, deterministic metrics) and the full
  evaluation with a live target and judge in a separate job or marker.
- A test that calls a model costs money every run. Use recorded outputs, or rely on the judge cache.
