"""Which Ananke Plexus this Guage Kit supports, and what the installed one can do.

Negotiation is explicit: Guage Kit reads the installed harness version, checks it against ``SUPPORTED_ANANKE`` and
probes the interfaces it calls. An out-of-range or incomplete harness is reported with a stable code
(``GK-HARNESS-001``) by ``guage doctor``, never silently worked around.
"""

from __future__ import annotations

import importlib
import re
from importlib import metadata
from typing import Any

SUPPORTED_ANANKE = ">=0.3.45,<0.4"  # keep in step with pyproject.toml (tests/test_packaging.py)

# capability id -> (module, attribute path). Required ones are what this release of Guage Kit calls.
CAPABILITIES: dict[str, tuple[str, str]] = {
    "evals.models": ("ananke.plexus.evals.models", "EvalScore"),
    "evals.trace": ("ananke.plexus.evals.models", "AgentTrace"),
    "evals.normalize": ("ananke.plexus.evals.traces.normalize", "normalize_trace"),
    "evals.gate": ("ananke.plexus.evals.policy.decisions", "apply_gate_policy"),
    "evals.evidence": ("ananke.plexus.evals.runner", "save_eval_evidence"),
    "evals.evaluators": ("ananke.plexus.evals.evaluators.base", "Evaluator"),
    "evals.statistics": ("ananke.plexus.evals.regression.statistics", "summary_statistics"),
    "evals.judge_envelope": ("ananke.plexus.evals.judges.base", "JudgeInputEnvelope"),
    "evals.judge_agreement": (
        "ananke.plexus.evals.evaluators.meta.calibration",
        "judge_human_agreement",
    ),
    "evals.markdown": ("ananke.plexus.evals.reports.markdown", "generate_markdown_report"),
    "evals.junit": ("ananke.plexus.evals.reports.junit", "generate_junit_xml"),
}
REQUIRED = ("evals.models", "evals.trace", "evals.normalize", "evals.gate", "evals.evaluators")


def parse_version(text: str) -> tuple[int, int, int] | None:
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)", text.strip())
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def _bounds() -> tuple[tuple[int, ...], tuple[int, ...]]:
    m = re.fullmatch(r">=([\d.]+),<([\d.]+)", SUPPORTED_ANANKE)
    assert m is not None  # noqa: S101 - a constant
    return tuple(int(p) for p in m.group(1).split(".")), tuple(
        int(p) for p in m.group(2).split(".")
    )


def supported(version: str) -> bool:
    parsed = parse_version(version)
    lo, hi = _bounds()
    return parsed is not None and lo <= parsed < hi


def installed_version(distribution: str = "ananke-plexus") -> str | None:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return None


def probe(capabilities: dict[str, tuple[str, str]] = CAPABILITIES) -> dict[str, bool]:
    """Which capabilities the importable harness exposes (imports only; nothing runs)."""
    found: dict[str, bool] = {}
    for cap, (module, attr_path) in capabilities.items():
        try:
            # module names come from the fixed CAPABILITIES table above, never from input
            obj: object = importlib.import_module(
                module
            )  # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
            for part in attr_path.split("."):
                obj = getattr(obj, part)
            found[cap] = True
        except (ImportError, AttributeError):
            found[cap] = False
    return found


def check() -> dict[str, Any]:
    """The negotiation verdict ``guage doctor`` prints."""
    version = installed_version()
    caps = probe()
    missing = [c for c in REQUIRED if not caps.get(c)]
    reasons: list[str] = []
    if version is None:
        reasons.append("ananke-plexus is not installed")
    elif not supported(version):
        reasons.append(f"ananke-plexus {version} is outside {SUPPORTED_ANANKE} (GK-HARNESS-001)")
    if missing:
        reasons.append(f"missing required capabilities: {', '.join(missing)}")
    return {
        "ananke_version": version,
        "supported_range": SUPPORTED_ANANKE,
        "compatible": version is not None and supported(version) and not missing,
        "capabilities": caps,
        "missing_required": missing,
        "reasons": reasons,
    }


__all__ = [
    "CAPABILITIES",
    "REQUIRED",
    "SUPPORTED_ANANKE",
    "check",
    "installed_version",
    "parse_version",
    "probe",
    "supported",
]
