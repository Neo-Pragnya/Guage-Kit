"""Shared text utilities: normalisation, tokenisation, n-grams, sentence and claim splitting."""

from __future__ import annotations

import re
import string
import unicodedata
from collections import Counter
from collections.abc import Sequence

_WORD = re.compile(r"\w+(?:[-']\w+)*", re.UNICODE)
_ARTICLES = re.compile(r"\b(a|an|the)\b", re.IGNORECASE)
_PUNCT = set(string.punctuation) | {"“", "”", "‘", "’", "—", "–", "…"}
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9])")
_CITATION = re.compile(r"\s*\[\d+(?:,\s*\d+)*\]")
_NUMBER = re.compile(r"[-+]?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?")

STOPWORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "of",
        "to",
        "in",
        "on",
        "at",
        "by",
        "for",
        "with",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "it's",
        "he",
        "she",
        "they",
        "them",
        "his",
        "her",
        "their",
        "we",
        "our",
        "you",
        "your",
        "i",
        "me",
        "my",
        "not",
        "no",
        "do",
        "does",
        "did",
        "done",
        "have",
        "has",
        "had",
        "having",
        "so",
        "such",
        "than",
        "too",
        "very",
        "can",
        "could",
        "should",
        "would",
        "will",
        "shall",
        "may",
        "might",
        "must",
        "there",
        "here",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "when",
        "where",
        "why",
        "how",
        "all",
        "any",
        "both",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "own",
        "same",
        "just",
        "also",
        "into",
        "over",
        "under",
        "about",
        "above",
        "below",
        "up",
        "down",
        "out",
        "off",
        "again",
        "further",
        "once",
        "only",
        "s",
        "t",
    ]
)


def normalize(text: str) -> str:
    """SQuAD-style answer normalisation: lower case, no punctuation, no articles, single spaces."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = "".join(ch for ch in text if ch not in _PUNCT)
    text = _ARTICLES.sub(" ", text)
    return " ".join(text.split())


def tokens(text: str, *, lower: bool = True) -> list[str]:
    text = unicodedata.normalize("NFKC", text)
    if lower:
        text = text.lower()
    return _WORD.findall(text)


def content_tokens(text: str) -> list[str]:
    return [t for t in tokens(text) if t not in STOPWORDS]


def ngrams(seq: Sequence[str], n: int) -> Counter[tuple[str, ...]]:
    return Counter(tuple(seq[i : i + n]) for i in range(len(seq) - n + 1))


def sentences(text: str) -> list[str]:
    """Split prose into sentences (a light rule-based splitter: no model, deterministic)."""
    text = " ".join(text.split())
    if not text:
        return []
    parts = _SENTENCE.split(text)
    out: list[str] = []
    for part in parts:
        for line in re.split(r"\s*(?:\n|•|;\s+(?=[A-Z]))\s*", part):
            if line.strip():
                out.append(line.strip())
    return out


def claims(text: str, *, min_words: int = 3) -> list[str]:
    """Atomic-ish claims: sentences, further split on coordinating ``and``/``but`` between clauses."""
    out: list[str] = []
    text = _CITATION.sub("", text)
    for s in sentences(text):
        pieces = re.split(r",?\s+(?:and|but|while|whereas)\s+(?=[a-z]+\s+\w+)", s)
        for p in pieces:
            if len(tokens(p)) >= min_words:
                out.append(p.strip(" ,"))
            elif out:
                out[-1] = out[-1] + " " + p
            elif p.strip():
                out.append(p.strip())
    return out


def numbers(text: str) -> list[float]:
    out: list[float] = []
    for m in _NUMBER.findall(text):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            continue
    return out


def lcs_length(a: Sequence[str], b: Sequence[str]) -> int:
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def f1(precision: float, recall: float) -> float:
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def overlap_f1(pred: Sequence[str], ref: Sequence[str]) -> tuple[float, float, float]:
    """Bag-of-tokens precision, recall and F1 (the SQuAD token-F1)."""
    if not pred and not ref:
        return 1.0, 1.0, 1.0
    if not pred or not ref:
        return 0.0, 0.0, 0.0
    common = Counter(pred) & Counter(ref)
    same = sum(common.values())
    if same == 0:
        return 0.0, 0.0, 0.0
    p = same / len(pred)
    r = same / len(ref)
    return p, r, f1(p, r)


def support(claim: str, evidence: str) -> float:
    """How much of a claim's content is found in the evidence: content-token recall with bigram backing.

    1.0 means every content word (and every content bigram) of the claim appears in the evidence. Numbers must
    match exactly: a claim with a number the evidence doesn't contain gets at most 0.5.
    """
    c = content_tokens(claim)
    if not c:
        return 1.0
    ev = set(content_tokens(evidence))
    uni = sum(1 for t in c if t in ev) / len(c)
    bi_c = ngrams(c, 2)
    if bi_c:
        ev_bi = ngrams(content_tokens(evidence), 2)
        bi = sum(min(n, ev_bi[g]) for g, n in bi_c.items()) / sum(bi_c.values())
        score = 0.7 * uni + 0.3 * bi
    else:
        score = uni
    claim_numbers = set(numbers(claim))
    if claim_numbers and not claim_numbers <= set(numbers(evidence)):
        score = min(score, 0.5)
    return score
