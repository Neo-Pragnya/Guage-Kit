"""Reference-based text metrics: exact and fuzzy matching, token F1, BLEU, chrF, ROUGE, edit distance, diversity.

All of them are implemented here in plain Python (no model download, deterministic). BLEU and chrF follow the
sacreBLEU definitions (13a-style tokenisation, brevity penalty, exponential smoothing for sentence BLEU; chrF with
character 6-grams and beta 2, chrF++ adds word bigrams). ROUGE follows Lin (2004) without stemming.
"""

from __future__ import annotations

import math
import re
import string
from collections import Counter

from guage_kit.core.sample import Sample
from guage_kit.metrics import _text as T
from guage_kit.metrics.registry import REGISTRY, corpus_metric, metric

_F = "text"


def _best(values: list[float]) -> float:
    return max(values) if values else 0.0


# ── matching ─────────────────────────────────────────────────────────────────────────────────────────────────────
@metric("exact_match", family=_F, requires=("output", "expected"))
def exact_match(sample: Sample, *, strip: bool = True, case_sensitive: bool = True) -> float:
    """1 when the output equals any reference exactly (after stripping whitespace)."""
    out = sample.output_text.strip() if strip else sample.output_text
    for ref in sample.expected_texts:
        r = ref.strip() if strip else ref
        if (out == r) if case_sensitive else (out.lower() == r.lower()):
            return 1.0
    return 0.0


@metric(
    "normalized_match",
    family=_F,
    requires=("output", "expected"),
    reference="SQuAD v1.1 evaluation script",
)
def normalized_match(sample: Sample) -> float:
    """1 when the normalised output (lower case, no punctuation or articles) equals a normalised reference."""
    out = T.normalize(sample.output_text)
    return float(any(out == T.normalize(r) for r in sample.expected_texts))


@metric(
    "token_f1", family=_F, requires=("output", "expected"), reference="SQuAD v1.1 evaluation script"
)
def token_f1(sample: Sample, *, normalize: bool = True) -> tuple[float, dict[str, float]]:
    """Bag-of-words F1 between output and the best-matching reference."""
    pred = T.normalize(sample.output_text).split() if normalize else T.tokens(sample.output_text)
    best = (0.0, 0.0, 0.0)
    for ref in sample.expected_texts:
        r = T.normalize(ref).split() if normalize else T.tokens(ref)
        cand = T.overlap_f1(pred, r)
        if cand[2] >= best[2]:
            best = cand
    return best[2], {"precision": round(best[0], 4), "recall": round(best[1], 4)}


@metric("contains", family=_F, requires=("output", "expected"))
def contains(sample: Sample, *, case_sensitive: bool = False) -> float:
    """1 when any reference appears inside the output (substring match)."""
    out = sample.output_text if case_sensitive else sample.output_text.lower()
    return float(
        any(
            (r if case_sensitive else r.lower()).strip() in out
            for r in sample.expected_texts
            if r.strip()
        )
    )


@metric("keyword_coverage", family=_F, requires=("output",))
def keyword_coverage(
    sample: Sample, *, keywords: tuple[str, ...] = ()
) -> tuple[float, dict[str, list[str]]] | None:
    """Share of required keywords present in the output. Keywords come from the parameter or ``metadata.keywords``."""
    kws = list(keywords) or list(sample.metadata.get("keywords") or [])
    if not kws:
        return None
    out = sample.output_text.lower()
    missing = [k for k in kws if k.lower() not in out]
    return 1 - len(missing) / len(kws), {"missing": missing}


@metric("regex_match", family=_F, requires=("output",))
def regex_match(sample: Sample, *, pattern: str = "", full: bool = False) -> float | None:
    """1 when the output matches the pattern (parameter, or ``metadata.pattern``)."""
    pat = pattern or sample.metadata.get("pattern")
    if not pat:
        return None
    fn = re.fullmatch if full else re.search
    return float(fn(str(pat), sample.output_text.strip(), re.DOTALL) is not None)


@metric("numeric_match", family=_F, requires=("output", "expected"))
def numeric_match(
    sample: Sample, *, rel_tol: float = 1e-6, abs_tol: float = 1e-9, last: bool = True
) -> tuple[float, dict[str, float]] | None:
    """1 when the (last) number in the output equals the expected number within tolerance (math word problems)."""
    got = T.numbers(sample.output_text)
    want: list[float] = []
    for ref in sample.expected_texts:
        want.extend(T.numbers(ref))
    if not want:
        return None
    if not got:
        return 0.0, {"expected": want[0]}
    value = got[-1] if last else got[0]
    ok = any(math.isclose(value, w, rel_tol=rel_tol, abs_tol=abs_tol) for w in want)
    return float(ok), {"found": value, "expected": want[0]}


# ── similarity ───────────────────────────────────────────────────────────────────────────────────────────────────
@metric("levenshtein_similarity", family=_F, requires=("output", "expected"))
def levenshtein_similarity(sample: Sample) -> float:
    """1 − edit distance / length of the longer string, against the closest reference (character level)."""
    out = sample.output_text.strip()
    best = 0.0
    for ref in sample.expected_texts:
        r = ref.strip()
        longest = max(len(out), len(r))
        best = max(best, 1.0 if longest == 0 else 1 - T.levenshtein(out, r) / longest)
    return best


@metric("jaccard", family=_F, requires=("output", "expected"))
def jaccard(sample: Sample) -> float:
    """Jaccard overlap of the word sets of output and the best reference."""
    a = set(T.tokens(sample.output_text))
    scores = []
    for ref in sample.expected_texts:
        b = set(T.tokens(ref))
        scores.append(1.0 if not a and not b else len(a & b) / len(a | b))
    return _best(scores)


# ── ROUGE ────────────────────────────────────────────────────────────────────────────────────────────────────────
def _rouge_n(pred: list[str], ref: list[str], n: int) -> tuple[float, float, float]:
    p_ng, r_ng = T.ngrams(pred, n), T.ngrams(ref, n)
    overlap = sum((p_ng & r_ng).values())
    p = overlap / max(sum(p_ng.values()), 1)
    r = overlap / max(sum(r_ng.values()), 1)
    return p, r, T.f1(p, r)


def _rouge_l(pred: list[str], ref: list[str]) -> tuple[float, float, float]:
    lcs = T.lcs_length(pred, ref)
    p = lcs / len(pred) if pred else 0.0
    r = lcs / len(ref) if ref else 0.0
    return p, r, T.f1(p, r)


_ROUGE_SPLIT = re.compile(r"[^a-z0-9]+")


def rouge_tokens(text: str, tokenizer: str = "default") -> list[str]:
    """``default``: the reference ROUGE tokeniser (lower-case ASCII letters and digits). ``unicode``: any script."""
    if tokenizer == "unicode":
        return T.tokens(text)
    return [t for t in _ROUGE_SPLIT.split(text.lower()) if t]


def _rouge_lsum(pred: str, ref: str, tokenizer: str = "default") -> tuple[float, float, float]:
    """Summary-level ROUGE-L: union LCS over sentences."""
    ps = [rouge_tokens(s, tokenizer) for s in T.sentences(pred)]
    rs = [rouge_tokens(s, tokenizer) for s in T.sentences(ref)]
    pred_len = sum(len(s) for s in ps)
    ref_len = sum(len(s) for s in rs)
    hits = 0
    pred_counts = Counter(t for s in ps for t in s)
    ref_counts = Counter(t for s in rs for t in s)
    for r_sent in rs:
        union: set[int] = set()
        for p_sent in ps:
            union |= _lcs_positions(r_sent, p_sent)
        for i in sorted(union):
            tok = r_sent[i]
            if pred_counts[tok] > 0 and ref_counts[tok] > 0:
                hits += 1
                pred_counts[tok] -= 1
                ref_counts[tok] -= 1
    p = hits / pred_len if pred_len else 0.0
    r = hits / ref_len if ref_len else 0.0
    return p, r, T.f1(p, r)


def _lcs_positions(a: list[str], b: list[str]) -> set[int]:
    n, m = len(a), len(b)
    table = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(m):
            table[i + 1][j + 1] = (
                table[i][j] + 1 if a[i] == b[j] else max(table[i][j + 1], table[i + 1][j])
            )
    out: set[int] = set()
    i, j = n, m
    while i > 0 and j > 0:
        if a[i - 1] == b[j - 1]:
            out.add(i - 1)
            i -= 1
            j -= 1
        elif table[i - 1][j] >= table[i][j - 1]:
            i -= 1
        else:
            j -= 1
    return out


@metric("rouge", family=_F, requires=("output", "expected"), reference="Lin (2004), ROUGE")
def rouge(
    sample: Sample, *, variant: str = "rougeL", measure: str = "f", tokenizer: str = "default"
) -> tuple[float, dict[str, float]]:
    """ROUGE F-measure (or precision/recall) against the best reference. Variants: rouge1, rouge2, rougeL, rougeLsum.
    ``tokenizer='unicode'`` keeps non-ASCII words (the reference tokeniser drops them)."""
    pred = rouge_tokens(sample.output_text, tokenizer)
    best = (0.0, 0.0, 0.0)
    for ref in sample.expected_texts:
        if variant == "rougeLsum":
            cand = _rouge_lsum(sample.output_text, ref, tokenizer)
        elif variant == "rougeL":
            cand = _rouge_l(pred, rouge_tokens(ref, tokenizer))
        elif variant.startswith("rouge") and variant[5:].isdigit():
            cand = _rouge_n(pred, rouge_tokens(ref, tokenizer), int(variant[5:]))
        else:
            raise ValueError(f"unknown ROUGE variant {variant!r}")
        if cand[2] >= best[2]:
            best = cand
    idx = {"p": 0, "precision": 0, "r": 1, "recall": 1}.get(measure, 2)
    return best[idx], {
        "precision": round(best[0], 4),
        "recall": round(best[1], 4),
        "f": round(best[2], 4),
    }


REGISTRY.variant("rouge1", "rouge", "ROUGE-1 F-measure (unigram overlap).", variant="rouge1")
REGISTRY.variant("rouge2", "rouge", "ROUGE-2 F-measure (bigram overlap).", variant="rouge2")
REGISTRY.variant(
    "rougeL", "rouge", "ROUGE-L F-measure (longest common subsequence).", variant="rougeL"
)
REGISTRY.variant(
    "rougeLsum",
    "rouge",
    "ROUGE-Lsum F-measure (summary-level LCS over sentences).",
    variant="rougeLsum",
)


# ── BLEU ─────────────────────────────────────────────────────────────────────────────────────────────────────────
_BLEU_TOK = [
    (re.compile(r"([\{-\~\[-\` -\&\(-\+\:-\@\/])"), r" \1 "),
    (re.compile(r"([^0-9])([\.,])"), r"\1 \2 "),
    (re.compile(r"([\.,])([^0-9])"), r" \1 \2"),
    (re.compile(r"([0-9])(-)"), r"\1 \2 "),
]


def bleu_tokenize(text: str) -> list[str]:
    """13a-style tokenisation (the sacreBLEU default)."""
    text = text.replace("<skipped>", "").replace("-\n", "").replace("\n", " ")
    text = (
        text.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    )
    text = f" {text} "
    for pattern, repl in _BLEU_TOK:
        text = pattern.sub(repl, text)
    return text.split()


def _bleu_stats(
    hyp: list[str], refs: list[list[str]], max_n: int
) -> tuple[list[int], list[int], int, int]:
    matches, totals = [0] * max_n, [0] * max_n
    for n in range(1, max_n + 1):
        h = T.ngrams(hyp, n)
        max_ref: Counter[tuple[str, ...]] = Counter()
        for r in refs:
            for g, c in T.ngrams(r, n).items():
                max_ref[g] = max(max_ref[g], c)
        matches[n - 1] = sum(min(c, max_ref[g]) for g, c in h.items())
        totals[n - 1] = max(len(hyp) - n + 1, 0)
    ref_len = min((abs(len(r) - len(hyp)), len(r)) for r in refs)[1] if refs else 0
    return matches, totals, len(hyp), ref_len


def _bleu_from_stats(
    matches: list[int], totals: list[int], hyp_len: int, ref_len: int, smooth: bool
) -> float:
    if hyp_len == 0:
        return 0.0
    # sentence BLEU uses the effective order (orders the hypothesis is long enough for), like sacreBLEU
    order = sum(1 for t in totals if t > 0) if smooth else len(matches)
    if order == 0:
        return 0.0
    log_p = 0.0
    k = 1.0
    for n in range(order):
        if totals[n] == 0 or matches[n] == 0:
            if not smooth:
                return 0.0
            k *= 2
            p = 1.0 / (k * max(totals[n], 1))
        else:
            p = matches[n] / totals[n]
        log_p += math.log(p) / order
    bp = 1.0 if hyp_len > ref_len else math.exp(1 - ref_len / hyp_len)
    return bp * math.exp(log_p)


@metric(
    "sentence_bleu",
    family=_F,
    requires=("output", "expected"),
    reference="Papineni et al. (2002); sacreBLEU exp smoothing",
)
def sentence_bleu(sample: Sample, *, max_order: int = 4) -> float:
    """BLEU of one output against its references, with exponential smoothing (0–1 scale)."""
    refs = [bleu_tokenize(r) for r in sample.expected_texts]
    m, t, h, r = _bleu_stats(bleu_tokenize(sample.output_text), refs, max_order)
    return _bleu_from_stats(m, t, h, r, smooth=True)


@corpus_metric(
    "bleu",
    family=_F,
    requires=("output", "expected"),
    reference="Papineni et al. (2002); sacreBLEU",
)
def bleu(samples: list[Sample], *, max_order: int = 4) -> tuple[float, dict[str, object]]:
    """Corpus BLEU (0–1): n-gram precisions pooled over all samples, with the brevity penalty."""
    M, Tt = [0] * max_order, [0] * max_order
    H = R = 0
    for s in samples:
        refs = [bleu_tokenize(r) for r in s.expected_texts]
        m, t, h, r = _bleu_stats(bleu_tokenize(s.output_text), refs, max_order)
        M = [a + b for a, b in zip(M, m, strict=True)]
        Tt = [a + b for a, b in zip(Tt, t, strict=True)]
        H += h
        R += r
    value = _bleu_from_stats(M, Tt, H, R, smooth=False)
    precisions = [round(m / t, 4) if t else 0.0 for m, t in zip(M, Tt, strict=True)]
    return value, {
        "precisions": precisions,
        "brevity_penalty": round(1.0 if H > R else math.exp(1 - R / H) if H else 0.0, 4),
        "hyp_len": H,
        "ref_len": R,
    }


# ── chrF ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def _chr_stats(hyp: str, ref: str, char_order: int, word_order: int) -> list[tuple[int, int, int]]:
    stats: list[tuple[int, int, int]] = []
    h_chars, r_chars = "".join(hyp.split()), "".join(ref.split())  # all whitespace, as sacreBLEU
    for n in range(1, char_order + 1):
        h = Counter(h_chars[i : i + n] for i in range(len(h_chars) - n + 1))
        r = Counter(r_chars[i : i + n] for i in range(len(r_chars) - n + 1))
        stats.append((sum((h & r).values()), sum(h.values()), sum(r.values())))
    hw, rw = _chrf_words(hyp), _chrf_words(ref)
    for n in range(1, word_order + 1):
        h2, r2 = T.ngrams(hw, n), T.ngrams(rw, n)
        stats.append((sum((h2 & r2).values()), sum(h2.values()), sum(r2.values())))
    return stats


def _chrf_words(text: str) -> list[str]:
    """chrF++ words: split on whitespace, then separate one trailing (or else one leading) ASCII punctuation mark."""
    out: list[str] = []
    for w in text.split():
        if len(w) > 1 and w[-1] in string.punctuation:
            out.extend([w[:-1], w[-1]])
        elif len(w) > 1 and w[0] in string.punctuation:
            out.extend([w[0], w[1:]])
        else:
            out.append(w)
    return out


def _chrf_score(stats: list[tuple[int, int, int]], beta: float) -> float:
    precs, recs = [], []
    for match, hyp, ref in stats:
        if hyp > 0 and ref > 0:
            precs.append(match / hyp)
            recs.append(match / ref)
    if not precs:
        return 0.0
    p, r = sum(precs) / len(precs), sum(recs) / len(recs)
    if p + r == 0:
        return 0.0
    b2 = beta * beta
    return (1 + b2) * p * r / (b2 * p + r)


@metric(
    "chrf",
    family=_F,
    requires=("output", "expected"),
    reference="Popović (2015, 2017); sacreBLEU chrF",
)
def chrf(sample: Sample, *, char_order: int = 6, word_order: int = 0, beta: float = 2.0) -> float:
    """Character n-gram F-score against the best reference (0–1). ``word_order=2`` gives chrF++."""
    return _best(
        [
            _chrf_score(_chr_stats(sample.output_text, r, char_order, word_order), beta)
            for r in sample.expected_texts
        ]
    )


REGISTRY.variant("chrf_pp", "chrf", "chrF++: character 6-grams plus word bigrams.", word_order=2)


@corpus_metric(
    "corpus_chrf", family=_F, requires=("output", "expected"), reference="sacreBLEU corpus chrF"
)
def corpus_chrf(
    samples: list[Sample], *, char_order: int = 6, word_order: int = 0, beta: float = 2.0
) -> float:
    """Corpus chrF: statistics pooled over all samples, using each sample's best-matching reference."""
    total: list[tuple[int, int, int]] | None = None
    for s in samples:
        st = max(
            (_chr_stats(s.output_text, r, char_order, word_order) for r in s.expected_texts),
            key=lambda x: _chrf_score(x, beta),
        )
        total = (
            st
            if total is None
            else [(a + x, b + y, c + z) for (a, b, c), (x, y, z) in zip(total, st, strict=True)]
        )
    return _chrf_score(total or [], beta)


# ── shape, length, diversity, readability ────────────────────────────────────────────────────────────────────────
@metric(
    "length_ratio",
    family=_F,
    requires=("output", "expected"),
    value_range=(0.0, None),
    higher_is_better=False,
)
def length_ratio(sample: Sample) -> float:
    """Output words ÷ reference words. 1 is the same length. Lower-is-better only when used as a maximum."""
    ref = max((len(T.tokens(r)) for r in sample.expected_texts), default=0)
    return len(T.tokens(sample.output_text)) / ref if ref else float("nan")


@metric("word_count", family=_F, requires=("output",), value_range=(0.0, None))
def word_count(
    sample: Sample, *, minimum: int = 0, maximum: int = 0
) -> tuple[float, dict[str, bool]]:
    """Number of words in the output. With ``minimum``/``maximum`` the details say whether it is within bounds."""
    n = len(T.tokens(sample.output_text))
    ok = (n >= minimum) and (maximum <= 0 or n <= maximum)
    return float(n), {"within_bounds": ok}


@metric("within_length", family=_F, requires=("output",))
def within_length(sample: Sample, *, minimum: int = 0, maximum: int = 200) -> float:
    """1 when the output word count is within [minimum, maximum]."""
    n = len(T.tokens(sample.output_text))
    return float(minimum <= n <= maximum)


def _syllables(word: str) -> int:
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and count > 1 and not word.endswith("le"):
        count -= 1
    return max(count, 1)


@metric(
    "flesch_reading_ease",
    family=_F,
    requires=("output",),
    value_range=(None, 121.22),
    reference="Flesch (1948)",
)
def flesch_reading_ease(sample: Sample) -> float:
    """Flesch reading ease of the output (higher is easier; 60–70 is plain English)."""
    words = T.tokens(sample.output_text)
    sents = max(len(T.sentences(sample.output_text)), 1)
    if not words:
        return float("nan")
    syl = sum(_syllables(w) for w in words)
    return 206.835 - 1.015 * (len(words) / sents) - 84.6 * (syl / len(words))


@corpus_metric("distinct_n", family=_F, requires=("output",), reference="Li et al. (2016)")
def distinct_n(samples: list[Sample], *, k: int = 2) -> float:
    """Distinct-n: unique n-grams ÷ all n-grams over every output (diversity; ``distinct_n@1`` for unigrams)."""
    all_ng: Counter[tuple[str, ...]] = Counter()
    for s in samples:
        all_ng.update(T.ngrams(T.tokens(s.output_text), k))
    total = sum(all_ng.values())
    return len(all_ng) / total if total else 0.0


@corpus_metric(
    "self_bleu",
    family=_F,
    requires=("output",),
    higher_is_better=False,
    reference="Zhu et al. (2018), Texygen",
)
def self_bleu(samples: list[Sample], *, max_order: int = 4, limit: int = 200) -> float | None:
    """Mean BLEU of each output against all the others. Lower means more diverse outputs."""
    outs = [bleu_tokenize(s.output_text) for s in samples[:limit]]
    if len(outs) < 2:
        return None
    vals = []
    for i, h in enumerate(outs):
        refs = outs[:i] + outs[i + 1 :]
        m, t, hl, rl = _bleu_stats(h, refs, max_order)
        vals.append(_bleu_from_stats(m, t, hl, rl, smooth=True))
    return sum(vals) / len(vals)
