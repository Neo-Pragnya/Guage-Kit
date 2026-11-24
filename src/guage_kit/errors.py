"""Stable error codes. Every error Guage Kit raises on purpose carries one, so scripts and CI can branch on it.

Add a code here before using it (tests/test_errors.py checks that codes are unique and documented).
"""

from __future__ import annotations

CODES: dict[str, str] = {
    "GK-DATA-001": "dataset file not found",
    "GK-DATA-002": "unsupported dataset format",
    "GK-DATA-003": "invalid sample in dataset",
    "GK-DATA-004": "dataset is empty",
    "GK-METRIC-001": "unknown metric",
    "GK-METRIC-002": "invalid metric parameters",
    "GK-METRIC-003": "metric needs an optional extra that is not installed",
    "GK-TARGET-001": "target could not be imported",
    "GK-TARGET-002": "target call failed",
    "GK-JUDGE-001": "judge provider is not configured",
    "GK-JUDGE-002": "judge returned an unparseable verdict",
    "GK-JUDGE-003": "judge provider call failed",
    "GK-CONFIG-001": "invalid suite configuration",
    "GK-RUN-001": "run not found",
    "GK-RUN-002": "runs cannot be compared",
    "GK-HARNESS-001": "installed Ananke Plexus is outside the supported range",
    "GK-HARNESS-002": "unknown Ananke evaluator",
    "GK-REPORT-001": "report could not be written",
}


class GuageError(Exception):
    """An expected failure with a stable code and a human explanation."""

    def __init__(self, code: str, message: str, *, hint: str | None = None) -> None:
        if code not in CODES:  # pragma: no cover - guarded by tests
            raise ValueError(f"unregistered error code {code}")
        self.code = code
        self.message = message
        self.hint = hint
        super().__init__(f"[{code}] {message}" + (f" (hint: {hint})" if hint else ""))


__all__ = ["CODES", "GuageError"]
