"""Datasets: load, validate, fingerprint, slice and save collections of samples.

Supported files: JSON Lines (``.jsonl``), JSON (a list, or an object with ``samples``), CSV and YAML. Field names
from common tools are mapped to the sample model (``question`` → ``input``, ``ground_truth`` → ``expected`` …).
Anything unrecognised is kept in ``metadata``, never dropped.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from guage_kit.core.sample import Sample
from guage_kit.errors import GuageError

ALIASES: dict[str, str] = {
    "question": "input",
    "query": "input",
    "prompt": "input",
    "user_input": "input",
    "messages": "input",
    "answer": "output",
    "response": "output",
    "prediction": "output",
    "completion": "output",
    "generated": "output",
    "ground_truth": "expected",
    "reference": "expected",
    "target": "expected",
    "gold": "expected",
    "ideal": "expected",
    "ground_truths": "references",
    "retrieved_contexts": "contexts",
    "context": "contexts",
    "documents": "contexts",
    "predicted_label": "label",
    "probs": "probabilities",
    "expected_tools": "expected_tool_calls",
    "tools": "tool_calls",
}
_FIELDS = set(Sample.model_fields)
_LIST_FIELDS = {"references", "contexts", "retrieved_ids", "relevant_ids", "tags"}


def normalise_record(record: dict[str, Any], index: int) -> dict[str, Any]:
    """Map a raw record onto sample fields. Unknown keys move into ``metadata``."""
    out: dict[str, Any] = {}
    metadata: dict[str, Any] = dict(record.get("metadata") or {})
    for key, value in record.items():
        if key == "metadata":
            continue
        target = key if key in _FIELDS else ALIASES.get(key)
        if target is None or (target in out and key not in _FIELDS):
            metadata[key] = value
            continue
        out[target] = value
    for key in _LIST_FIELDS:
        value = out.get(key)
        if isinstance(value, str):
            out[key] = _split_list(value)
    out.setdefault("id", str(record.get("id", index)))
    out["id"] = str(out["id"])
    if metadata:
        out["metadata"] = metadata
    return out


def _split_list(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("["):
        try:
            loaded = json.loads(value)
            if isinstance(loaded, list):
                return [str(v) for v in loaded]
        except json.JSONDecodeError:
            pass
    if "|" in value:
        return [v.strip() for v in value.split("|") if v.strip()]
    return [value] if value else []


class Dataset:
    """An ordered collection of samples with a stable content fingerprint."""

    def __init__(
        self, samples: Iterable[Sample], *, name: str = "dataset", source: str = ""
    ) -> None:
        self.samples: list[Sample] = list(samples)
        self.name = name
        self.source = source
        ids = [s.id for s in self.samples]
        dupes = [i for i, n in Counter(ids).items() if n > 1]
        if dupes:
            raise GuageError(
                "GK-DATA-003",
                f"duplicate sample ids: {', '.join(dupes[:5])}",
                hint="every sample needs a unique id",
            )

    # ── construction ───────────────────────────────────────────────────────
    @classmethod
    def from_records(
        cls, records: Iterable[dict[str, Any]], *, name: str = "dataset", source: str = ""
    ) -> Dataset:
        samples: list[Sample] = []
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise GuageError("GK-DATA-003", f"record {index} is not an object")
            try:
                samples.append(Sample.model_validate(normalise_record(record, index)))
            except ValidationError as exc:
                first = exc.errors()[0]
                where = ".".join(str(p) for p in first["loc"])
                raise GuageError(
                    "GK-DATA-003", f"record {index} ({where}): {first['msg']}"
                ) from exc
        return cls(samples, name=name, source=source)

    @classmethod
    def load(cls, path: str | Path, *, name: str | None = None) -> Dataset:
        p = Path(path)
        if not p.is_file():
            raise GuageError("GK-DATA-001", f"dataset not found: {p}")
        suffix = p.suffix.lower()
        text = p.read_text(encoding="utf-8")
        records: list[dict[str, Any]]
        if suffix in (".jsonl", ".ndjson"):
            records = []
            for line_no, line in enumerate(text.splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise GuageError("GK-DATA-003", f"{p.name}:{line_no}: {exc.msg}") from exc
        elif suffix == ".json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise GuageError("GK-DATA-003", f"{p.name}: {exc.msg}") from exc
            records = _records_from_document(data, p)
        elif suffix in (".yaml", ".yml"):
            records = _records_from_document(yaml.safe_load(text), p)
        elif suffix in (".csv", ".tsv"):
            reader = csv.DictReader(text.splitlines(), delimiter="\t" if suffix == ".tsv" else ",")
            records = [_parse_csv_row(row) for row in reader]
        else:
            raise GuageError(
                "GK-DATA-002",
                f"unsupported dataset format {suffix or '(none)'}",
                hint="use .jsonl, .json, .yaml, .csv or .tsv",
            )
        return cls.from_records(records, name=name or p.stem, source=str(p))

    # ── container protocol ─────────────────────────────────────────────────
    def __len__(self) -> int:
        return len(self.samples)

    def __iter__(self) -> Iterator[Sample]:
        return iter(self.samples)

    def __getitem__(self, index: int) -> Sample:
        return self.samples[index]

    def get(self, sample_id: str) -> Sample | None:
        return next((s for s in self.samples if s.id == sample_id), None)

    # ── identity ───────────────────────────────────────────────────────────
    @property
    def fingerprint(self) -> str:
        """sha256 over the canonical JSON of every sample: equal data, equal fingerprint."""
        h = hashlib.sha256()
        for s in self.samples:
            h.update(
                json.dumps(
                    s.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, default=str
                ).encode("utf-8")
            )
            h.update(b"\n")
        return "sha256:" + h.hexdigest()

    @property
    def input_fingerprint(self) -> str:
        """sha256 over ids, inputs and references only: two runs of different systems on the same test set match."""
        h = hashlib.sha256()
        for s in self.samples:
            h.update(
                json.dumps(
                    [s.id, s.input, s.expected, s.references, s.relevant_ids],
                    sort_keys=True,
                    ensure_ascii=False,
                    default=str,
                ).encode("utf-8")
            )
            h.update(b"\n")
        return "sha256:" + h.hexdigest()

    # ── transforms (each returns a new dataset) ────────────────────────────
    def filter(self, predicate: Callable[[Sample], bool], *, name: str | None = None) -> Dataset:
        return Dataset(
            [s for s in self.samples if predicate(s)], name=name or self.name, source=self.source
        )

    def with_tag(self, tag: str) -> Dataset:
        return self.filter(lambda s: tag in s.tags, name=f"{self.name}[{tag}]")

    def sample(self, n: int, *, seed: int = 0) -> Dataset:
        if n >= len(self.samples):
            return Dataset(self.samples, name=self.name, source=self.source)
        rng = random.Random(seed)
        picked = sorted(rng.sample(range(len(self.samples)), n))
        return Dataset(
            [self.samples[i] for i in picked], name=f"{self.name}[n={n}]", source=self.source
        )

    def split(self, fraction: float, *, seed: int = 0) -> tuple[Dataset, Dataset]:
        if not 0 < fraction < 1:
            raise GuageError("GK-DATA-003", "split fraction must be between 0 and 1")
        order = list(range(len(self.samples)))
        random.Random(seed).shuffle(order)
        cut = round(len(order) * fraction)
        first = sorted(order[:cut])
        second = sorted(order[cut:])
        return (
            Dataset([self.samples[i] for i in first], name=f"{self.name}[a]", source=self.source),
            Dataset([self.samples[i] for i in second], name=f"{self.name}[b]", source=self.source),
        )

    def map(self, fn: Callable[[Sample], Sample]) -> Dataset:
        return Dataset([fn(s) for s in self.samples], name=self.name, source=self.source)

    # ── persistence ────────────────────────────────────────────────────────
    def to_records(self) -> list[dict[str, Any]]:
        return [s.model_dump(mode="json", exclude_defaults=True) for s in self.samples]

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        records = self.to_records()
        suffix = p.suffix.lower()
        if suffix in (".jsonl", ".ndjson"):
            p.write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8"
            )
        elif suffix == ".json":
            p.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        elif suffix in (".yaml", ".yml"):
            p.write_text(
                yaml.safe_dump(records, sort_keys=False, allow_unicode=True), encoding="utf-8"
            )
        elif suffix in (".csv", ".tsv"):
            # nested values (lists, objects) are written as JSON, which the loader reads back
            import io

            columns: list[str] = []
            for r in records:
                columns.extend(k for k in r if k not in columns)
            buf = io.StringIO()
            writer = csv.DictWriter(
                buf,
                fieldnames=columns,
                delimiter="\t" if suffix == ".tsv" else ",",
                lineterminator="\n",
            )
            writer.writeheader()
            for r in records:
                writer.writerow(
                    {
                        k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                        for k, v in r.items()
                    }
                )
            p.write_text(buf.getvalue(), encoding="utf-8")
        else:
            raise GuageError(
                "GK-DATA-002",
                f"cannot save as {suffix}",
                hint="use .jsonl, .json, .yaml, .csv or .tsv",
            )
        return p

    # ── description ────────────────────────────────────────────────────────
    def stats(self) -> dict[str, Any]:
        """Which fields are populated, tag counts and text lengths: what can be measured on this data."""
        fields = [f for f in Sample.model_fields if f not in {"id", "tags", "metadata"}]
        coverage = {
            f: sum(1 for s in self.samples if (s.label is not None if f == "label" else s.has(f)))
            for f in fields
        }
        tags = Counter(t for s in self.samples for t in s.tags)
        lengths = [len(s.output_text.split()) for s in self.samples if s.has("output")]
        return {
            "name": self.name,
            "samples": len(self.samples),
            "fingerprint": self.fingerprint,
            "fields": {f: n for f, n in coverage.items() if n},
            "tags": dict(tags.most_common()),
            "output_words": {
                "mean": round(sum(lengths) / len(lengths), 1) if lengths else 0,
                "max": max(lengths) if lengths else 0,
            },
        }


def _records_from_document(data: Any, path: Path) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        for key in ("samples", "data", "cases", "examples", "rows"):
            if isinstance(data.get(key), list):
                return list(data[key])
        raise GuageError(
            "GK-DATA-003",
            f"{path.name}: expected a list of samples or an object with 'samples'",
        )
    if isinstance(data, list):
        return data
    raise GuageError("GK-DATA-003", f"{path.name}: expected a list of samples")


def _parse_csv_row(row: dict[str, str | None]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if key is None:
            continue
        if value is None or value == "":
            continue
        stripped = value.strip()
        if stripped[:1] in "[{":
            try:
                out[key] = json.loads(stripped)
                continue
            except json.JSONDecodeError:
                pass
        out[key] = value
    return out


def load_dataset(path: str | Path, *, name: str | None = None) -> Dataset:
    """Load a dataset file (``.jsonl``, ``.json``, ``.yaml``, ``.csv``, ``.tsv``)."""
    return Dataset.load(path, name=name)


__all__ = ["ALIASES", "Dataset", "load_dataset", "normalise_record"]
