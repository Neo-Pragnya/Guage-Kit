"""RAG metrics: is the retrieved context any good, and is the answer grounded in it?

Every metric works offline with a transparent lexical method (content-word and bigram support, exact numbers).
With a judge configured, ``method="judge"`` asks the judge to verify each claim against the evidence instead
(natural-language inference). The details of each score list the claims and whether each was supported, so a
reviewer can see why a number is what it is.
"""

from __future__ import annotations

import re
from typing import Any

from guage_kit.core.sample import Sample
from guage_kit.metrics import _text as T
from guage_kit.metrics.registry import MetricContext, metric

_F = "rag"


def _supported(
    claim: str, evidence: list[str], method: str, threshold: float, ctx: MetricContext | None
) -> tuple[bool, float]:
    if method == "judge":
        if ctx is None or ctx.judge is None:
            raise ValueError(
                "method='judge' needs a judge (pass judge= to evaluate or configure one in guage.yaml)"
            )
        score = float(ctx.judge.entailment(premise="\n\n".join(evidence), hypothesis=claim))
        return score >= 0.5, score
    best = max((T.support(claim, e) for e in evidence), default=0.0)
    joined = T.support(claim, " ".join(evidence))
    score = max(best, joined)
    return score >= threshold, score


def _claim_table(
    claims: list[str], evidence: list[str], method: str, threshold: float, ctx: MetricContext | None
) -> tuple[float, list[dict[str, Any]]]:
    rows = []
    for c in claims:
        ok, s = _supported(c, evidence, method, threshold, ctx)
        rows.append({"claim": c, "supported": ok, "support": round(s, 3)})
    share = sum(1 for r in rows if r["supported"]) / len(rows) if rows else 1.0
    return share, rows


@metric(
    "faithfulness",
    family=_F,
    requires=("output", "contexts"),
    reference="Es et al. (2023), faithfulness",
)
def faithfulness(
    sample: Sample,
    *,
    method: str = "lexical",
    threshold: float = 0.6,
    ctx: MetricContext | None = None,
) -> tuple[float, dict[str, Any]] | None:
    """Share of the answer's claims that the retrieved contexts support (groundedness)."""
    claims = T.claims(sample.output_text)
    if not claims:
        return None
    share, rows = _claim_table(claims, sample.contexts, method, threshold, ctx)
    unsupported = [r["claim"] for r in rows if not r["supported"]]
    return share, {
        "claims": rows,
        "unsupported": unsupported,
        "reason": f"{len(rows) - len(unsupported)}/{len(rows)} claims supported",
    }


@metric("hallucination_rate", family=_F, requires=("output", "contexts"), higher_is_better=False)
def hallucination_rate(
    sample: Sample,
    *,
    method: str = "lexical",
    threshold: float = 0.6,
    ctx: MetricContext | None = None,
) -> tuple[float, dict[str, Any]] | None:
    """Share of the answer's claims that nothing in the contexts supports (1 − faithfulness)."""
    res = faithfulness(sample, method=method, threshold=threshold, ctx=ctx)
    if res is None:
        return None
    return 1 - res[0], {"unsupported": res[1]["unsupported"]}


@metric(
    "context_recall",
    family=_F,
    requires=("contexts", "expected"),
    reference="Es et al. (2023), context recall",
)
def context_recall(
    sample: Sample,
    *,
    method: str = "lexical",
    threshold: float = 0.6,
    ctx: MetricContext | None = None,
) -> tuple[float, dict[str, Any]] | None:
    """Share of the reference answer's claims that the retrieved contexts contain: did retrieval find what was needed?"""
    claims = T.claims(sample.expected_texts[0])
    if not claims:
        return None
    share, rows = _claim_table(claims, sample.contexts, method, threshold, ctx)
    return share, {"claims": rows}


def _chunk_relevant(sample: Sample, i: int, chunk: str, threshold: float) -> bool:
    if sample.relevant_ids and i < len(sample.retrieved_ids):
        return sample.retrieved_ids[i] in set(sample.relevant_ids)
    refs = sample.expected_texts
    if refs:
        return any(T.support(c, chunk) >= threshold for r in refs for c in T.claims(r) or [r])
    q = T.content_tokens(sample.input_text)
    if not q:
        return False
    chunk_tokens = set(T.content_tokens(chunk))
    return sum(1 for t in q if t in chunk_tokens) / len(q) >= threshold


@metric(
    "context_precision",
    family=_F,
    requires=("contexts",),
    reference="Es et al. (2023), context precision",
)
def context_precision(
    sample: Sample, *, threshold: float = 0.5
) -> tuple[float, dict[str, Any]] | None:
    """Rank-aware precision of the contexts: are relevant chunks ranked above irrelevant ones?

    Relevance comes from ``relevant_ids`` when present, otherwise from support of the reference answer (or, with
    neither, overlap with the question).
    """
    if not sample.expected_texts and not sample.relevant_ids and not sample.input_text:
        return None
    flags = [_chunk_relevant(sample, i, c, threshold) for i, c in enumerate(sample.contexts)]
    if not any(flags):
        return 0.0, {"relevant": flags}
    hits = 0
    total = 0.0
    for i, f in enumerate(flags, 1):
        if f:
            hits += 1
            total += hits / i
    return total / hits, {"relevant": flags}


@metric("context_relevance", family=_F, requires=("input", "contexts"))
def context_relevance(sample: Sample, *, threshold: float = 0.3) -> tuple[float, dict[str, Any]]:
    """Share of context sentences that relate to the question (noise in the retrieved text)."""
    q = set(T.content_tokens(sample.input_text))
    sents = [s for c in sample.contexts for s in T.sentences(c)]
    if not sents or not q:
        return 0.0, {}
    rel = 0
    for s in sents:
        st = set(T.content_tokens(s))
        if st and len(st & q) / min(len(q), len(st)) >= threshold:
            rel += 1
    return rel / len(sents), {"sentences": len(sents), "relevant": rel}


@metric("context_utilization", family=_F, requires=("output", "contexts"))
def context_utilization(
    sample: Sample, *, threshold: float = 0.6
) -> tuple[float, dict[str, Any]] | None:
    """Share of retrieved chunks the answer actually draws on (low values mean wasted context)."""
    claims = T.claims(sample.output_text)
    if not claims:
        return None
    used = [any(T.support(c, chunk) >= threshold for c in claims) for chunk in sample.contexts]
    return sum(used) / len(used), {"used": used}


@metric(
    "answer_relevancy",
    family=_F,
    requires=("input", "output"),
    reference="Es et al. (2023), answer relevancy",
)
def answer_relevancy(
    sample: Sample, *, method: str = "auto", ctx: MetricContext | None = None
) -> tuple[float, dict[str, Any]]:
    """How directly the answer addresses the question.

    With an embedder (``method='auto'`` or ``'embedding'``): cosine similarity of question and answer. Without one:
    coverage of the question's content words in the answer, discounted for evasive or refusing answers.
    """
    from guage_kit.metrics.safety import is_refusal

    if method in ("auto", "embedding") and ctx is not None and ctx.embedder is not None:
        from guage_kit.metrics.semantic import cosine

        a, b = ctx.embedder.embed([sample.input_text, sample.output_text])
        return max(0.0, cosine(a, b)), {"method": "embedding"}
    if method == "embedding":
        raise ValueError("method='embedding' needs an embedder (install guage-kit[embeddings])")
    q = T.content_tokens(sample.input_text)
    a = set(T.content_tokens(sample.output_text))
    coverage = sum(1 for t in q if t in a) / len(q) if q else 0.0
    # an answer that echoes the question but adds nothing is not relevant
    novelty = len(a - set(q)) / len(a) if a else 0.0
    score = 0.6 * coverage + 0.4 * min(1.0, novelty * 1.5)
    if is_refusal(sample.output_text):
        score *= 0.2
    return min(1.0, score), {"method": "lexical", "coverage": round(coverage, 3)}


_CITE = re.compile(r"\[(\d+)\]")


@metric("citation_accuracy", family=_F, requires=("output", "contexts"))
def citation_accuracy(
    sample: Sample, *, threshold: float = 0.5
) -> tuple[float, dict[str, Any]] | None:
    """Share of citations ``[n]`` whose cited context (1-based) supports the sentence that cites it."""
    checks = []
    for sent in T.sentences(sample.output_text):
        refs = [int(n) for n in _CITE.findall(sent)]
        claim = _CITE.sub("", sent).strip()
        for n in refs:
            ok = (
                1 <= n <= len(sample.contexts)
                and T.support(claim, sample.contexts[n - 1]) >= threshold
            )
            checks.append({"sentence": claim, "cites": n, "supported": ok})
    if not checks:
        return None
    return sum(1 for c in checks if c["supported"]) / len(checks), {"citations": checks}


@metric("citation_coverage", family=_F, requires=("output",))
def citation_coverage(sample: Sample) -> float | None:
    """Share of answer sentences that carry at least one ``[n]`` citation."""
    sents = T.sentences(sample.output_text)
    if not sents:
        return None
    return sum(1 for s in sents if _CITE.search(s)) / len(sents)


@metric(
    "answer_correctness",
    family=_F,
    requires=("output", "expected"),
    reference="Es et al. (2023), answer correctness",
)
def answer_correctness(
    sample: Sample, *, threshold: float = 0.6
) -> tuple[float, dict[str, Any]] | None:
    """Claim-level F1 between answer and reference: precision (answer claims the reference backs) and recall."""
    ans, ref = T.claims(sample.output_text), T.claims(sample.expected_texts[0])
    if not ans or not ref:
        return None
    ref_text, ans_text = " ".join(ref), " ".join(ans)
    tp_p = sum(1 for c in ans if T.support(c, ref_text) >= threshold)
    tp_r = sum(1 for c in ref if T.support(c, ans_text) >= threshold)
    p, r = tp_p / len(ans), tp_r / len(ref)
    if len(T.content_tokens(ref_text)) <= 4:
        # a short reference ("Paris") is a fact to find in the answer, not a text to match claim by claim
        return r, {
            "precision": None,
            "recall": round(r, 3),
            "reason": "short reference: recall only",
        }
    return T.f1(p, r), {"precision": round(p, 3), "recall": round(r, 3)}
