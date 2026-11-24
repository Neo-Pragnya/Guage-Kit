"""Report guarantees: offline, CSP-locked, hostile text stays inert, public profile strips text, formats are valid."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from guage_kit.core.sample import Sample
from guage_kit.reports import junit, markdown, write_all, write_report
from guage_kit.reports.html import safe_json
from guage_kit.runner import compare, evaluate

HOSTILE = "</script><script>window.__pwned=1</script><img src=x onerror=alert(1)> {{MANIFEST}} \u2028 http://evil.example/x"


def _run(output: str = "Paris is the capital.") -> object:
    return evaluate(
        [
            Sample(
                id="h1",
                input=HOSTILE,
                output=output,
                expected="Paris",
                contexts=["Paris is the capital of France."],
                tags=["t"],
            ),
            Sample(id="h2", input="q", output="Paris", expected="Paris", tags=["t"]),
        ],
        ["token_f1", "faithfulness", "bleu"],
        gates=[{"metric": "token_f1", "min": 0.9}],
        slices=["tags"],
    )


def test_html_is_offline_and_csp_locked(tmp_path: Path) -> None:
    page = write_report(_run(), tmp_path / "r.html").read_text(encoding="utf-8")
    csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', page).group(1)  # type: ignore[union-attr]
    assert (
        "default-src 'none'" in csp and "connect-src 'none'" in csp and "unsafe-inline" not in csp
    )
    scripts = re.findall(r"<script>(.*?)</script>", page, re.DOTALL)
    assert len(scripts) == 1
    digest = (
        "'sha256-" + base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode() + "'"
    )
    assert digest in csp
    style = re.search(r"<style>(.*?)</style>", page, re.DOTALL).group(1)  # type: ignore[union-attr]
    assert (
        "'sha256-" + base64.b64encode(hashlib.sha256(style.encode()).digest()).decode() + "'" in csp
    )
    # no external resource can be referenced by the template itself
    assert not re.search(r'(src|href)="https?://', page)


def test_hostile_text_cannot_break_out(tmp_path: Path) -> None:
    page = write_report(_run(), tmp_path / "r.html").read_text(encoding="utf-8")
    data = re.search(
        r'<script type="application/json" id="guage-data">(.*?)</script>', page, re.DOTALL
    ).group(1)  # type: ignore[union-attr]
    assert "</script>" not in data and "<img" not in data and "\u2028" not in data
    model = json.loads(data)
    assert model["samples"][0]["input"] == HOSTILE  # round-trips exactly as text
    manifest = re.search(r'id="guage-manifest">(.*?)</script>', page, re.DOTALL).group(1)  # type: ignore[union-attr]
    assert (
        json.loads(manifest)["schema"] == "guage-kit/report-manifest@1"
    )  # not replaced by the hostile placeholder
    js = (Path(__file__).parents[1] / "src/guage_kit/reports/assets/report.js").read_text(
        encoding="utf-8"
    )
    assert (
        "innerHTML" not in js
        and "eval(" not in js
        and "fetch(" not in js
        and "localStorage" not in js
    )


def test_safe_json_escapes() -> None:
    assert safe_json({"a": "</script>&\u2029"}) == '{"a":"\\u003c/script\\u003e\\u0026\\u2029"}'


def test_public_profile_strips_text(tmp_path: Path) -> None:
    page = write_report(_run(), tmp_path / "p.html", profile="public").read_text(encoding="utf-8")
    model = json.loads(re.search(r'id="guage-data">(.*?)</script>', page, re.DOTALL).group(1))  # type: ignore[union-attr]
    assert (
        model["profile"] == "public" and "input" not in model["samples"][0] and model["limitations"]
    )
    assert "Paris is the capital." not in page and "git" not in model["run"]["environment"]


def test_comparison_report(tmp_path: Path) -> None:
    a, b = _run("Berlin."), _run()
    page = write_report(b, tmp_path / "c.html", comparison=compare(a, b)).read_text(
        encoding="utf-8"
    )
    model = json.loads(re.search(r'id="guage-data">(.*?)</script>', page, re.DOTALL).group(1))  # type: ignore[union-attr]
    assert model["comparison"]["metrics"]["token_f1"]["delta"] > 0


def test_markdown_and_junit(tmp_path: Path) -> None:
    run = _run()
    md = markdown(run)
    assert "| token_f1 ↑ |" in md and "Gate:" in md
    root = ET.fromstring(junit(run))
    assert root.tag == "testsuite" and int(root.get("failures", "0")) >= 1
    files = write_all(run, tmp_path / "all")
    assert {p.name for p in files.values()} == {
        "report.html",
        "summary.md",
        "junit.xml",
        "run.json",
    }


def test_demo_runs_offline(tmp_path: Path) -> None:
    from guage_kit.demo import run_demo

    files = run_demo(tmp_path)
    assert files["rag_compare"].stat().st_size > 20_000
    summary = files["summary"].read_text(encoding="utf-8")
    assert "Support assistant v2" in summary and "improved" in summary
