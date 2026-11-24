"""pytest integration: evaluations as tests.

Installed automatically with Guage Kit (entry point ``pytest11``). It adds:

- the ``guage`` fixture: ``guage.evaluate(...)`` runs an evaluation and records it for the session report;
  ``guage.check(run, faithfulness=0.8, latency_p95=("<=", 1200))`` fails the test with a readable message;
- ``guage.assert_metric("token_f1", output, expected, minimum=0.6)`` for one-off checks of a single output;
- ``--guage-report=path.html`` (and ``--guage-junit``) to write every recorded run into one report directory;
- a terminal summary of the recorded runs.

The plugin imports nothing heavy until a test uses the fixture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


class GuageFixture:
    def __init__(self, request: pytest.FixtureRequest) -> None:
        self._request = request

    def evaluate(self, *args: Any, **kwargs: Any) -> Any:
        from guage_kit.runner.evaluate import evaluate

        kwargs.setdefault("name", self._request.node.name)
        run = evaluate(*args, **kwargs)
        self._request.config.stash.setdefault(_RUNS, []).append((self._request.node.nodeid, run))
        return run

    def check(self, run: Any, **bars: Any) -> None:
        """``metric=minimum`` or ``metric=("<=", maximum)``. Also fails when the run's gate blocked."""
        problems = []
        for metric, bar in bars.items():
            name = metric.replace("__at__", "@")
            value = run.value(name)
            op, limit = (">=", bar) if not isinstance(bar, tuple) else bar
            if value is None:
                problems.append(f"{name}: no value")
            elif (op == ">=" and value < limit) or (op == "<=" and value > limit):
                problems.append(f"{name} = {value:.4g}, expected {op} {limit}")
        if run.gate is not None and run.gate.verdict == "BLOCK":
            problems += [f"gate: {e}" for e in run.gate.evidence]
        if problems:
            pytest.fail("Guage Kit quality bar missed:\n  " + "\n  ".join(problems), pytrace=False)

    def score(self, metric: str, output: Any, expected: Any = None, **fields: Any) -> float | None:
        from guage_kit.core.sample import Sample
        from guage_kit.metrics.registry import MetricContext, get_metric, resolve
        from guage_kit.metrics.semantic import HashingEmbedder

        get_metric(metric.partition("@")[0])
        judge = fields.pop("judge", None)
        params = fields.pop("params", {})
        sample = Sample(id="assert", output=output, expected=expected, **fields)
        bm = resolve({"name": metric, "params": params})
        from guage_kit.judges.judge import make_judge

        ctx = MetricContext(judge=make_judge(judge), embedder=HashingEmbedder())
        if bm.info.level == "corpus":
            return bm.compute([sample], ctx).value
        sc = bm.score(sample, ctx)
        if sc.error:
            pytest.fail(f"{metric} errored: {sc.error}", pytrace=False)
        return sc.value

    def assert_metric(
        self,
        metric: str,
        output: Any,
        expected: Any = None,
        *,
        minimum: float | None = None,
        maximum: float | None = None,
        **fields: Any,
    ) -> float:
        value = self.score(metric, output, expected, **fields)
        if value is None:
            pytest.fail(f"{metric} could not score this output (missing fields?)", pytrace=False)
        if minimum is not None and value < minimum:
            pytest.fail(
                f"{metric} = {value:.4g} < {minimum}\noutput: {str(output)[:300]!r}", pytrace=False
            )
        if maximum is not None and value > maximum:
            pytest.fail(
                f"{metric} = {value:.4g} > {maximum}\noutput: {str(output)[:300]!r}", pytrace=False
            )
        return value


_RUNS = pytest.StashKey[list[tuple[str, Any]]]()


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("guage-kit")
    group.addoption(
        "--guage-report",
        default=None,
        help="Directory for HTML reports of evaluations run in tests.",
    )
    group.addoption(
        "--guage-junit",
        default=None,
        help="Write a JUnit XML file per recorded run into this directory.",
    )


@pytest.fixture
def guage(request: pytest.FixtureRequest) -> GuageFixture:
    """Evaluate inside tests and check quality bars (Guage Kit)."""
    return GuageFixture(request)


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: pytest.Config) -> None:
    runs = config.stash.get(_RUNS, [])
    if not runs:
        return
    terminalreporter.section("Guage Kit")
    for nodeid, run in runs:
        verdict = run.gate.verdict if run.gate else "–"
        top = ", ".join(
            f"{k}={v.value:.3f}" for k, v in list(run.summaries.items())[:4] if v.value is not None
        )
        terminalreporter.write_line(f"{nodeid}: {verdict} · {top}")
    report_dir = config.getoption("--guage-report")
    junit_dir = config.getoption("--guage-junit")
    if report_dir or junit_dir:
        from guage_kit.reports import junit, write_report

        for i, (_, run) in enumerate(runs):
            stem = f"{i:02d}-{''.join(c if c.isalnum() else '-' for c in run.name)[:60]}"
            if report_dir:
                p = write_report(run, Path(report_dir) / f"{stem}.html")
                terminalreporter.write_line(f"report: {p}")
            if junit_dir:
                jp = Path(junit_dir) / f"{stem}.xml"
                jp.parent.mkdir(parents=True, exist_ok=True)
                jp.write_text(junit(run), encoding="utf-8")
