"""Render a run (and optionally a comparison) into one self-contained, offline HTML file.

Guarantees (tests/test_reports.py):

- **Offline.** CSS and JavaScript are inlined. No CDN, font, image or telemetry URL is referenced, and the page's
  Content Security Policy is ``default-src 'none'`` with the inline script and style allowed only by their sha256
  hashes, so nothing can load or connect even if injected.
- **Safe.** Data is embedded as JSON in ``<script type="application/json">`` with ``<``, ``>``, ``&`` and the
  U+2028/U+2029 separators escaped, so evaluated text (model outputs can be hostile) can never close the script.
  The page sets every piece of untrusted text with ``textContent``.
- **Shareable.** The ``public`` profile removes inputs, outputs, references, contexts and the git revision,
  keeping only scores. The manifest records which profile was used.
- **Traceable.** A manifest (renderer, versions, input digest, dataset fingerprint) is embedded in the page.
"""

from __future__ import annotations

import base64
import hashlib
import json
from importlib import (
    resources,
)  # nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2
from pathlib import Path
from typing import Any

from guage_kit.core.results import RunResult
from guage_kit.errors import GuageError
from guage_kit.version import __version__

RENDERER = "guage-kit/report-html@1"
VIEW_MODEL = "guage-kit/report-view@1"
LS, PS = chr(0x2028), chr(0x2029)
MAX_TEXT = 6000  # characters of any one text field kept in the page


def safe_json(data: Any) -> str:
    """JSON that is safe inside an HTML ``<script>`` element."""
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return (
        text.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace(LS, "\\u2028")
        .replace(PS, "\\u2029")
    )


def _clip(v: Any) -> Any:
    if isinstance(v, str):
        return (
            v if len(v) <= MAX_TEXT else v[:MAX_TEXT] + f"… [{len(v) - MAX_TEXT} more characters]"
        )
    if isinstance(v, list):
        return [_clip(x) for x in v[:200]]
    if isinstance(v, dict):
        return {str(k): _clip(x) for k, x in list(v.items())[:200]}
    return v


def view_model(
    run: RunResult, *, comparison: Any = None, profile: str = "private", title: str | None = None
) -> dict[str, Any]:
    if profile not in ("private", "public"):
        raise GuageError("GK-REPORT-001", f"unknown profile {profile!r}", hint="private or public")
    public = profile == "public"
    samples = []
    for s in run.samples:
        row: dict[str, Any] = {
            "id": s.sample_id,
            "tags": s.tags,
            "latency_ms": s.latency_ms,
            "target_error": s.target_error,
            "scores": {
                k: {
                    "value": sc.value,
                    "passed": sc.passed,
                    "skipped": sc.skipped,
                    "error": sc.error,
                    "reason": None if public else _clip(sc.reason),
                    "details": {} if public else _clip(sc.details),
                }
                for k, sc in s.scores.items()
            },
        }
        if not public:
            row.update(
                {
                    "input": _clip(s.input),
                    "output": _clip(s.output),
                    "expected": _clip(s.expected),
                    "repeats": _clip(s.repeats),
                }
            )
        samples.append(row)
    env = run.environment.model_dump() if run.environment else {}
    if public:
        env.pop("git", None)
    limitations = []
    if public:
        limitations.append(
            "public profile: inputs, outputs, references, score explanations and the git revision were removed"
        )
    model: dict[str, Any] = {
        "schema": VIEW_MODEL,
        "title": title or f"Guage Kit · {run.name}",
        "profile": profile,
        "run": {
            "run_id": run.run_id,
            "name": run.name,
            "created_at": run.created_at,
            "duration_s": run.duration_s,
            "dataset": run.dataset
            if not public
            else {k: v for k, v in run.dataset.items() if k != "source"},
            "target": run.target,
            "judge": run.judge,
            "metrics": run.metrics,
            "config": _clip(run.config),
            "environment": env,
            "notes": run.notes,
        },
        "summaries": {k: v.model_dump() for k, v in run.summaries.items()},
        "slices": {g: {k: v.model_dump() for k, v in ss.items()} for g, ss in run.slices.items()},
        "gate": run.gate.model_dump() if run.gate else None,
        "samples": samples,
        "comparison": None,
        "limitations": limitations,
    }
    if comparison is not None:
        c = comparison.model_dump(by_alias=True)
        if public:
            for key in ("regressions", "improvements"):
                for r in c.get(key, []):
                    r.pop("input", None)
                    r.pop("output_a", None)
                    r.pop("output_b", None)
            if c.get("pairwise"):
                c["pairwise"].pop("rows", None)
        model["comparison"] = _clip(c)
    return model


def _digest(model: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(safe_json(model).encode("utf-8")).hexdigest()


def _asset(name: str) -> str:
    return resources.files("guage_kit.reports").joinpath("assets", name).read_text(encoding="utf-8")


def _csp_hash(text: str) -> str:
    return (
        "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode() + "'"
    )


def render_html(model: dict[str, Any]) -> str:
    manifest = {
        "schema": "guage-kit/report-manifest@1",
        "renderer": RENDERER,
        "guage_kit": __version__,
        "ananke_plexus": model["run"]["environment"].get("ananke_plexus"),
        "view_model": model["schema"],
        "profile": model["profile"],
        "run_id": model["run"]["run_id"],
        "dataset_fingerprint": model["run"]["dataset"].get("fingerprint"),
        "input_digest": _digest(model),
        "publication": "offline-single-file",
        "limitations": model["limitations"],
    }
    css = _asset("report.css")
    js = _asset("report.js")
    csp = f"default-src 'none'; script-src {_csp_hash(js)}; style-src {_csp_hash(css)}; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'"
    import html as _html

    page = _asset("report.html")
    replacements = {
        "{{CSP}}": _html.escape(csp, quote=False).replace('"', "&quot;"),
        "{{TITLE}}": _html.escape(model["title"]),
        "{{CSS}}": css,
        "{{JS}}": js,
        "{{DATA}}": safe_json(model),
        "{{MANIFEST}}": safe_json(manifest),
    }
    # one pass: text inside DATA that looks like a placeholder is never substituted again
    import re

    return re.sub(
        r"\{\{(CSP|TITLE|CSS|JS|DATA|MANIFEST)\}\}", lambda m: replacements[m.group(0)], page
    )


def write_report(
    result: Any,
    path: str | Path,
    *,
    comparison: Any = None,
    profile: str = "private",
    title: str | None = None,
    run_b: RunResult | None = None,
) -> Path:
    """Write the HTML report. ``result`` is a run; pass ``comparison`` (and the candidate as the run) for a
    before/after report, or a :class:`~guage_kit.runner.compare.Comparison` together with ``run_b``."""
    from guage_kit.runner.compare import Comparison

    if isinstance(result, Comparison):
        if run_b is None:
            raise GuageError(
                "GK-REPORT-001", "a comparison report needs the candidate run (run_b=)"
            )
        comparison, result = result, run_b
    if not isinstance(result, RunResult):
        raise GuageError("GK-REPORT-001", f"cannot render {type(result).__name__}")
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            render_html(view_model(result, comparison=comparison, profile=profile, title=title)),
            encoding="utf-8",
        )
    except OSError as exc:
        raise GuageError("GK-REPORT-001", f"cannot write {p}: {exc}") from exc
    return p


__all__ = ["RENDERER", "render_html", "safe_json", "view_model", "write_report"]
