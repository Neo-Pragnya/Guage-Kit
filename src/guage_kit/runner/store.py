"""Run storage: ``.guage/runs/<run_id>/run.json``, ``latest``, and named baselines in ``.guage/baselines/``."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from guage_kit.core.results import RunResult
from guage_kit.errors import GuageError


class RunStore:
    """Saved runs under ``.guage/runs`` and named baselines under ``.guage/baselines``. ``load`` accepts a run id,
    a path, ``latest``, ``latest~N`` or ``baseline:<name>``."""

    def __init__(self, root: str | Path = ".guage/runs") -> None:
        self.root = Path(root)

    @property
    def baselines(self) -> Path:
        return self.root.parent / "baselines"

    def save(self, run: RunResult) -> Path:
        d = self.root / run.run_id
        run.save(d / "run.json")
        return d

    def list(self) -> list[dict[str, Any]]:
        if not self.root.is_dir():
            return []
        out = []
        for p in sorted(self.root.glob("*/run.json"), reverse=True):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            out.append(
                {
                    "run_id": data.get("run_id"),
                    "name": data.get("name"),
                    "created_at": data.get("created_at"),
                    "samples": len(data.get("samples", [])),
                    "verdict": (data.get("gate") or {}).get("verdict"),
                    "path": str(p),
                }
            )
        return out

    def resolve(self, ref: str | Path) -> Path:
        """A run id, ``latest``, ``latest~1``, ``baseline:<name>``, a run directory or a run.json path."""
        ref_s = str(ref)
        if ref_s.startswith("baseline:"):
            p = self.baselines / f"{ref_s.split(':', 1)[1]}.json"
            if not p.is_file():
                raise GuageError(
                    "GK-RUN-001",
                    f"no baseline named {ref_s.split(':', 1)[1]!r}",
                    hint="guage baseline set <run>",
                )
            return p
        if ref_s.startswith("latest"):
            runs = self.list()
            offset = int(ref_s.partition("~")[2] or 0)
            if len(runs) <= offset:
                raise GuageError("GK-RUN-001", f"no run {ref_s} in {self.root}")
            return Path(runs[offset]["path"])
        p = Path(ref_s)
        if p.is_file():
            return p
        if (p / "run.json").is_file():
            return p / "run.json"
        if (self.root / ref_s / "run.json").is_file():
            return self.root / ref_s / "run.json"
        raise GuageError(
            "GK-RUN-001", f"run not found: {ref_s}", hint="`guage runs` lists saved runs"
        )

    def load(self, ref: str | Path) -> RunResult:
        return RunResult.load(self.resolve(ref))

    def set_baseline(self, ref: str | Path, name: str = "main") -> Path:
        src = self.resolve(ref)
        self.baselines.mkdir(parents=True, exist_ok=True)
        dest = self.baselines / f"{name}.json"
        shutil.copyfile(src, dest)
        return dest


def load_run(ref: str | Path | RunResult, root: str | Path = ".guage/runs") -> RunResult:
    """Load a run from a reference (run id, path, ``latest``, ``latest~N`` or ``baseline:<name>``); a
    :class:`RunResult` is returned unchanged."""
    if isinstance(ref, RunResult):
        return ref
    return RunStore(root).load(ref)


__all__ = ["RunStore", "load_run"]
