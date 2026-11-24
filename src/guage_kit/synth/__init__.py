"""Synthetic test sets from your own documents.

:func:`chunk` splits documents into overlapping passages with stable ids. :func:`cloze_dataset` makes offline,
deterministic fill-in-the-blank questions: a sentence with a key span (a number or a proper noun) blanked out, the
span as the answer, and the source passage as the relevant context. That exercises retrieval and grounded answering
with no model at all. :func:`generate_qa` asks a model for natural questions instead, grounded in each passage and
returned as JSON (questions it cannot ground are dropped).
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from guage_kit.core.dataset import Dataset
from guage_kit.core.sample import Sample
from guage_kit.metrics import _text as T


def read_documents(paths: Iterable[str | Path]) -> list[tuple[str, str]]:
    """(name, text) for every .md, .txt, .rst and .html file under the given paths."""
    out: list[tuple[str, str]] = []
    for p in map(Path, paths):
        files = (
            sorted(f for f in p.rglob("*") if f.suffix.lower() in (".md", ".txt", ".rst", ".html"))
            if p.is_dir()
            else [p]
        )
        for f in files:
            text = f.read_text(encoding="utf-8", errors="replace")
            if f.suffix.lower() == ".html":
                text = re.sub(
                    r"<script.*?</script>|<style.*?</style>",
                    " ",
                    text,
                    flags=re.DOTALL | re.IGNORECASE,
                )
                text = re.sub(r"<[^>]+>", " ", text)
            out.append((f.name, text))
    return out


def chunk(
    documents: Sequence[tuple[str, str]], *, size: int = 120, overlap: int = 20
) -> list[dict[str, str]]:
    """Word-window chunks: ``{"id", "source", "text"}``. Ids hash the source, offset and text, so re-chunking is stable."""
    chunks: list[dict[str, str]] = []
    step = max(1, size - overlap)
    for name, text in documents:
        words = text.split()
        for start in range(0, max(len(words) - overlap, 1), step):
            piece = " ".join(words[start : start + size])
            if len(piece.split()) < 8:
                continue
            cid = hashlib.sha256(f"{name}:{start}:{piece}".encode()).hexdigest()[:12]
            chunks.append({"id": cid, "source": name, "text": piece})
    return chunks


_SPAN = re.compile(
    r"\b(\d[\d,.]*\s?(?:%|percent|years?|km|kg|m|million|billion)?|(?:[A-Z][a-z]+(?:\s+(?:of|de|the)?\s*[A-Z][a-z]+)*))\b"
)


def cloze_dataset(
    chunks: Sequence[dict[str, str]],
    *,
    per_chunk: int = 1,
    seed: int = 0,
    name: str = "synthetic-cloze",
) -> Dataset:
    """Offline test questions from document chunks: a salient term is blanked out of a sentence and becomes
    the expected answer, with the chunk as context and its id as the relevant document."""
    rng = random.Random(seed)
    samples: list[Sample] = []
    for c in chunks:
        sents = [s for s in T.sentences(c["text"]) if 8 <= len(s.split()) <= 40]
        rng.shuffle(sents)
        made = 0
        for s in sents:
            spans = [
                m.group(0).strip()
                for m in _SPAN.finditer(s)
                if m.start() > 0 and len(m.group(0).strip()) > 1
            ]
            if not spans:
                continue
            span = rng.choice(spans)
            question = "Fill in the blank: " + s.replace(span, "_____", 1)
            samples.append(
                Sample(
                    id=f"{c['id']}-{made}",
                    input=question,
                    expected=span,
                    relevant_ids=[c["id"]],
                    metadata={"source": c["source"], "passage": c["text"], "generator": "cloze"},
                    tags=["synthetic", "cloze"],
                )
            )
            made += 1
            if made >= per_chunk:
                break
    return Dataset(samples, name=name)


_QA_SYSTEM = (
    "You write evaluation questions for a question-answering system. Each question must be answerable from the "
    "passage alone, specific, and phrased as a real user would ask it. The answer must be short and copied or closely "
    "paraphrased from the passage. Reply with JSON only."
)


def generate_qa(
    chunks: Sequence[dict[str, str]],
    provider: Any,
    *,
    per_chunk: int = 2,
    name: str = "synthetic-qa",
) -> Dataset:
    """Natural questions from a model (any provider spec or object), grounded and checked against each passage."""
    from guage_kit.judges.judge import parse_json
    from guage_kit.judges.providers import make_provider

    prov = make_provider(provider)
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"},
                        "kind": {"type": "string"},
                    },
                    "required": ["question", "answer", "kind"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }
    samples: list[Sample] = []
    for c in chunks:
        prompt = (
            f"Write {per_chunk} question-answer pairs about this passage. Vary the kind: factual, why/how, comparison.\n"
            f'<untrusted name="passage">\n{c["text"]}\n</untrusted>\n'
            'Return JSON: {"items": [{"question": "...", "answer": "...", "kind": "factual|why|comparison"}]}'
        )
        try:
            data = parse_json(prov.complete(_QA_SYSTEM, prompt, json_schema=schema).text)
        except Exception:  # noqa: S112 - one bad passage must not stop generation
            continue
        for i, item in enumerate(data.get("items", [])[:per_chunk]):
            q, a = str(item.get("question", "")).strip(), str(item.get("answer", "")).strip()
            if not q or not a or T.support(a, c["text"]) < 0.5:
                continue  # drop answers the passage does not back
            samples.append(
                Sample(
                    id=f"{c['id']}-{i}",
                    input=q,
                    expected=a,
                    relevant_ids=[c["id"]],
                    metadata={
                        "source": c["source"],
                        "passage": c["text"],
                        "kind": item.get("kind", ""),
                        "generator": prov.name,
                    },
                    tags=["synthetic", str(item.get("kind") or "qa")],
                )
            )
    return Dataset(samples, name=name)


def write_corpus(chunks: Sequence[dict[str, str]], path: str | Path) -> Path:
    """Save chunks as JSON Lines, the corpus a retriever under test indexes."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks), encoding="utf-8"
    )
    return p


__all__ = ["chunk", "cloze_dataset", "generate_qa", "read_documents", "write_corpus"]
