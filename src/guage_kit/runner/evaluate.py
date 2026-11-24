"""``evaluate()``: run a target (optional), score every sample, aggregate with confidence intervals, slice, gate.

The whole run is described by the returned :class:`~guage_kit.core.results.RunResult`: data fingerprint, target,
metric parameters, judge usage, versions and git revision, so any report can say exactly what it measured.
"""

from __future__ import annotations

import os
import platform
import subprocess
import time
import uuid
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from guage_kit import stats
from guage_kit.core.dataset import Dataset
from guage_kit.core.results import (
    Environment,
    GateRule,
    MetricSummary,
    RunResult,
    SampleResult,
    Score,
)
from guage_kit.core.sample import Sample
from guage_kit.errors import GuageError
from guage_kit.metrics import _text as T
from guage_kit.metrics.registry import BoundMetric, MetricContext, resolve
from guage_kit.runner.target import Target, make_target
from guage_kit.version import __version__

MetricSpec = str | dict[str, Any] | BoundMetric


# ── automatic metric selection ───────────────────────────────────────────────────────────────────────────────────
def auto_metrics(samples: Sequence[Sample]) -> list[str]:
    """Pick sensible metrics from which fields the data has. Explicit lists always win; this is the default."""

    def share(pred: Callable[[Sample], bool]) -> float:
        return sum(1 for s in samples if pred(s)) / len(samples) if samples else 0.0

    def field_share(f: str) -> float:
        return share(lambda s: s.has(f))

    has = {
        f: field_share(f) >= 0.5
        for f in (
            "output",
            "expected",
            "contexts",
            "retrieved_ids",
            "relevant_ids",
            "relevance",
            "probabilities",
            "confidence",
            "expected_tool_calls",
            "tool_calls",
            "trace",
            "latency_ms",
            "usage",
            "embeddings",
        )
    }
    has["label"] = share(lambda s: s.label is not None) >= 0.5
    picked: list[str] = []
    classification = (has["label"] or has["probabilities"]) and has["expected"]
    if classification:
        picked += ["accuracy", "f1", "balanced_accuracy", "cohen_kappa"]
        if has["probabilities"] or has["confidence"]:
            picked += ["ece", "brier", "selective_auroc"]
    elif has["embeddings"] or (
        has["expected"]
        and share(
            lambda s: isinstance(s.expected, (int, float)) and not isinstance(s.expected, bool)
        )
        >= 0.5
    ):
        picked += ["sts_spearman", "sts_pearson"]
    elif has["output"] and has["expected"]:
        short = (
            share(lambda s: len(T.tokens(s.expected_texts[0] if s.expected_texts else "")) <= 4)
            >= 0.8
        )
        picked += (
            ["normalized_match", "contains", "token_f1"]
            if short
            else ["token_f1", "rougeL", "bleu", "chrf"]
        )
        picked.append("semantic_similarity")
        if share(lambda s: bool(T.numbers(s.expected_texts[0] if s.expected_texts else ""))) >= 0.8:
            picked.append("numeric_match")
    if has["retrieved_ids"] and (has["relevant_ids"] or has["relevance"]):
        picked += ["recall@5", "precision@5", "mrr", "ndcg@10", "hit_rate@5"]
    if has["contexts"]:
        if has["output"]:
            picked += ["faithfulness", "answer_relevancy", "context_utilization"]
        if has["expected"]:
            picked += ["context_recall", "context_precision"]
            if has["output"]:
                picked.append("answer_correctness")
    if has["expected_tool_calls"] and (has["tool_calls"] or has["trace"]):
        picked += ["tool_call_f1", "tool_args_accuracy", "tool_sequence_match", "tool_calls_exact"]
    if has["tool_calls"] or has["trace"]:
        picked += ["tool_error_rate", "redundant_tool_calls"]
    if share(lambda s: "should_refuse" in s.metadata) > 0:
        picked.append("refusal_correctness")
    if share(lambda s: "system_prompt" in s.metadata) > 0:
        picked.append("system_prompt_leakage")
    if share(lambda s: "canary" in s.metadata) > 0:
        picked.append("injection_resistance")
    if share(lambda s: "schema" in s.metadata) > 0:
        picked.append("json_schema")
    if share(lambda s: "success" in s.metadata) > 0:
        picked.append("goal_success")
    if share(lambda s: "counterfactual_group" in s.metadata) > 0:
        picked.append("counterfactual_consistency")
    if has["output"] and not classification:
        picked += ["pii_leakage", "secret_leakage", "toxicity"]
    if has["latency_ms"]:
        picked += ["latency_p50", "latency_p95"]
    if has["usage"]:
        picked.append("total_tokens")
        if share(lambda s: s.usage is not None and s.usage.cost_usd is not None) >= 0.5:
            picked += ["cost_usd", "total_cost_usd"]
    seen: set[str] = set()
    return [m for m in picked if not (m in seen or seen.add(m))]  # type: ignore[func-returns-value]


# ── helpers ──────────────────────────────────────────────────────────────────────────────────────────────────────
def _as_dataset(data: Dataset | Iterable[Sample | dict[str, Any]] | str | Path) -> Dataset:
    if isinstance(data, Dataset):
        return data
    if isinstance(data, (str, Path)):
        return Dataset.load(data)
    items = list(data)
    if items and all(isinstance(i, Sample) for i in items):
        return Dataset([i for i in items if isinstance(i, Sample)])
    return Dataset.from_records([i.model_dump() if isinstance(i, Sample) else i for i in items])


def _git(root: Path) -> dict[str, Any]:
    try:
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if head.returncode != 0:
            return {}
        dirty = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return {"commit": head.stdout.strip(), "dirty": bool(dirty.stdout.strip())}
    except (OSError, subprocess.TimeoutExpired):
        return {}


def environment(root: Path | None = None) -> Environment:
    """Describe the current environment (versions, platform, git commit and dirty state) for a run record."""
    from guage_kit.harness.negotiation import installed_version

    return Environment(
        guage_kit=__version__,
        ananke_plexus=installed_version(),
        python=platform.python_version(),
        platform=f"{platform.system()} {platform.machine()}",
        git=_git(root or Path.cwd()),
    )


def _now() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    moment = (
        datetime.fromtimestamp(int(epoch), UTC) if epoch and epoch.isdigit() else datetime.now(UTC)
    )
    return moment.replace(microsecond=0).isoformat()


def summarize(
    bm: BoundMetric,
    scores: list[Score],
    *,
    corpus_value: float | None = None,
    corpus_details: dict[str, Any] | None = None,
    confidence: float = 0.95,
    n_resamples: int = 1000,
    seed: int = 0,
) -> MetricSummary:
    """Summarise a metric over a run: mean of the sample scores (or the corpus value) with a bootstrap
    confidence interval, counts of scored, skipped and errored samples, and a histogram."""
    values = [s.value for s in scores if s.value is not None]
    lo_range, hi_range = bm.info.value_range
    s = MetricSummary(
        metric=bm.name,
        family=bm.info.family,
        description=bm.info.description,
        higher_is_better=bm.info.higher_is_better,
        level=bm.info.level,
        n=len(values),
        skipped=sum(1 for x in scores if x.skipped),
        errors=sum(1 for x in scores if x.error),
        threshold=bm.threshold,
        details=dict(corpus_details or {}),
    )
    if not bm.info.deterministic:
        s.details["judge"] = True
    if values:
        s.mean = stats.mean(values)
        s.median = stats.median(values)
        s.std = stats.stdev(values)
        s.min, s.max = min(values), max(values)
        if len(values) > 1:
            s.ci_low, s.ci_high = stats.bootstrap_ci(
                values, confidence=confidence, n_resamples=n_resamples, seed=seed
            )
        else:
            s.ci_low = s.ci_high = values[0]
        lo = lo_range if lo_range is not None else s.min
        hi = hi_range if hi_range is not None else s.max
        s.histogram, rng = stats.histogram(values, 10, lo, hi)
        s.histogram_range = rng
        passes = [x.passed for x in scores if x.passed is not None]
        s.pass_rate = sum(passes) / len(passes) if passes else None
    s.value = corpus_value if bm.info.level == "corpus" else s.mean
    if bm.info.level == "corpus":
        s.n = int((corpus_details or {}).get("n", s.n))
        if s.value is not None and bm.threshold is not None:
            ok = s.value >= bm.threshold if bm.info.higher_is_better else s.value <= bm.threshold
            s.pass_rate = 1.0 if ok else 0.0
    return s


def corpus_ci(
    bm: BoundMetric,
    samples: list[Sample],
    ctx: MetricContext,
    *,
    confidence: float = 0.95,
    n_resamples: int = 200,
    seed: int = 0,
) -> tuple[float | None, float | None]:
    """Bootstrap interval of a corpus metric: resample the samples, recompute the metric."""
    import random

    if not bm.info.deterministic or len(samples) < 2 or len(samples) > 20000:
        return None, None
    rng = random.Random(seed)
    n = len(samples)
    values: list[float] = []
    for _ in range(n_resamples):
        resample = [samples[rng.randrange(n)] for _ in range(n)]
        try:
            v = bm.compute(resample, ctx).value
        except Exception:  # noqa: S112 - a degenerate resample (e.g. one class) is skipped
            continue
        if v is not None:
            values.append(v)
    if len(values) < max(10, n_resamples // 4):
        return None, None
    alpha = (1 - confidence) / 2
    return stats.quantile(values, alpha), stats.quantile(values, 1 - alpha)


def _consistency(outputs: list[Any]) -> float | None:
    texts = [T.normalize(str(o)) for o in outputs if o is not None]
    if len(texts) < 2:
        return None
    pairs = [(a, b) for i, a in enumerate(texts) for b in texts[i + 1 :]]
    return sum(1.0 if a == b else T.overlap_f1(a.split(), b.split())[2] for a, b in pairs) / len(
        pairs
    )


# ── the engine ───────────────────────────────────────────────────────────────────────────────────────────────────
def evaluate(
    data: Dataset | Iterable[Sample | dict[str, Any]] | str | Path,
    metrics: Sequence[MetricSpec] | str | None = None,
    *,
    target: Any = None,
    judge: Any = None,
    embedder: Any = None,
    gates: Sequence[GateRule | dict[str, Any]] | None = None,
    slices: Sequence[str] | None = None,
    name: str = "",
    concurrency: int = 4,
    repeats: int = 1,
    confidence: float = 0.95,
    n_resamples: int = 1000,
    seed: int = 0,
    save: bool | str | Path = False,
    evidence: bool = False,
    project_root: str | Path = ".",
    progress: Callable[[str, int, int], None] | None = None,
    config: dict[str, Any] | None = None,
) -> RunResult:
    """Evaluate a dataset.

    Args:
        data: a :class:`Dataset`, a list of samples or dicts, or a dataset file path.
        metrics: metric names or specs (``"recall@5"``, ``{"name": "judge", "params": {...}, "threshold": 0.7}``),
            or ``None``/``"auto"`` to choose from the fields the data has.
        target: the system under test (a callable, ``module:function`` or a provider spec), run for samples
            without an output. ``repeats > 1`` runs it several times and reports ``self_consistency``.
        judge: a judge (``"heuristic"``, ``"anthropic:claude-opus-5-5"``, ``"ollama:llama3.1"`` … or an object).
        embedder: an embedder (``"hashing"``, a sentence-transformers model name, or an object).
        gates: quality bars, ``{"metric": "faithfulness", "min": 0.8, "on_fail": "block"}``. Decided by Ananke.
        slices: break results down by ``"tags"`` or by metadata keys (``"difficulty"``, ``"language"``).
        save: write the run under ``.guage/runs/`` (``True``) or into the given directory.
        evidence: also write an Ananke evidence bundle under ``.ananke/evidence/<run_id>/eval/``.
    """
    from guage_kit.judges.judge import make_judge
    from guage_kit.metrics.semantic import make_embedder

    started = time.perf_counter()
    root = Path(project_root)
    ds = _as_dataset(data)
    if not len(ds):
        raise GuageError("GK-DATA-004", "the dataset has no samples")
    # sortable to the microsecond, so `latest` is the newest run even when runs finish within one second
    run_id = f"{datetime.now(UTC).strftime('%Y%m%d-%H%M%S-%f')}-{uuid.uuid4().hex[:4]}"

    # 1. produce outputs
    tgt: Target | None = make_target(target)
    samples = list(ds.samples)
    results: dict[str, SampleResult] = {}
    repeats_out: dict[str, list[Any]] = {}
    if tgt is not None:
        todo = [s for s in samples if not s.has("output")]

        def run_one(s: Sample) -> tuple[Sample, str | None, list[Any]]:
            outs: list[Any] = []
            first: Sample | None = None
            err: str | None = None
            for _ in range(max(1, repeats)):
                try:
                    produced = tgt(s)
                    first = first or produced
                    outs.append(produced.output)
                except GuageError as exc:
                    err = exc.message
                    break
            return (first or s), err, outs

        done = 0
        produced_map: dict[str, tuple[Sample, str | None, list[Any]]] = {}
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
            for s, res in zip(todo, pool.map(run_one, todo), strict=True):
                produced_map[s.id] = res
                done += 1
                if progress:
                    progress("target", done, len(todo))
        new_samples = []
        for s in samples:
            if s.id in produced_map:
                ns, err, outs = produced_map[s.id]
                new_samples.append(ns)
                if err:
                    results[s.id] = SampleResult(sample_id=s.id, target_error=err)
                if len(outs) > 1:
                    repeats_out[s.id] = outs
            else:
                new_samples.append(s)
        samples = new_samples

    # 2. metrics
    if metrics is None or metrics == "auto":
        specs: list[MetricSpec] = list(auto_metrics(samples))
    elif isinstance(metrics, str):
        specs = [m.strip() for m in metrics.split(",") if m.strip()]
    else:
        specs = list(metrics)
    import guage_kit.metrics  # noqa: F401  (registers the built-ins)

    bound = [resolve(m) for m in specs]
    names = [b.name for b in bound]
    if len(set(names)) != len(names):
        raise GuageError(
            "GK-METRIC-002",
            "two metrics share a name",
            hint="give one of them a different 'as:' name",
        )
    if isinstance(judge, str) and judge not in ("", "heuristic", "offline"):
        from guage_kit.judges.judge import LLMJudge

        judge_obj: Any = LLMJudge(judge, cache_dir=root / ".guage" / "cache" / "judge")
    else:
        judge_obj = make_judge(judge)
    if judge_obj is None and any(b.info.needs_judge for b in bound):
        raise GuageError(
            "GK-JUDGE-001",
            f"{', '.join(b.name for b in bound if b.info.needs_judge)} need a judge",
            hint="pass judge='heuristic' (offline) or a model, e.g. 'anthropic:claude-opus-5-5'",
        )
    ctx = MetricContext(
        judge=judge_obj,
        embedder=make_embedder(embedder) if isinstance(embedder, str) else embedder,
        seed=seed,
    )

    for s in samples:
        results.setdefault(s.id, SampleResult(sample_id=s.id))
        r = results[s.id]
        r.input, r.output, r.expected, r.tags, r.latency_ms = (
            s.input,
            s.output,
            s.expected,
            list(s.tags),
            s.latency_ms,
        )
        if s.id in repeats_out:
            r.repeats = repeats_out[s.id]

    sample_metrics = [b for b in bound if b.info.level == "sample"]
    corpus = [b for b in bound if b.info.level == "corpus"]
    scorable = [s for s in samples if results[s.id].target_error is None]

    def score_sample(s: Sample) -> dict[str, Score]:
        return {b.name: b.score(s, ctx) for b in sample_metrics}

    workers = max(1, concurrency) if any(not b.info.deterministic for b in sample_metrics) else 1
    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            scored = list(pool.map(score_sample, scorable))
    else:
        scored = []
        for i, s in enumerate(scorable, 1):
            scored.append(score_sample(s))
            if progress:
                progress("score", i, len(scorable))
    for s, sc in zip(scorable, scored, strict=True):
        results[s.id].scores.update(sc)

    summaries: dict[str, MetricSummary] = {}
    for b in sample_metrics:
        summaries[b.name] = summarize(
            b,
            [results[s.id].scores[b.name] for s in scorable],
            confidence=confidence,
            n_resamples=n_resamples,
            seed=seed,
        )
    for b in corpus:
        try:
            out = b.compute(scorable, ctx)
        except GuageError:
            raise
        except Exception as exc:
            summaries[b.name] = MetricSummary(
                metric=b.name,
                family=b.info.family,
                description=b.info.description,
                level="corpus",
                higher_is_better=b.info.higher_is_better,
                errors=1,
                details={"error": f"{type(exc).__name__}: {exc}"},
            )
            continue
        per = [Score(metric=b.name, value=v, passed=b.passed(v)) for v in out.per_sample.values()]
        for sid, v in out.per_sample.items():
            if sid in results:
                results[sid].scores[b.name] = Score(metric=b.name, value=v, passed=b.passed(v))
        summaries[b.name] = summarize(
            b,
            per,
            corpus_value=out.value,
            corpus_details=out.details,
            confidence=confidence,
            n_resamples=n_resamples,
            seed=seed,
        )
        lo, hi = (
            corpus_ci(
                b,
                scorable,
                ctx,
                confidence=confidence,
                n_resamples=min(n_resamples, 200),
                seed=seed,
            )
            if out.value is not None
            else (None, None)
        )
        summaries[b.name].ci_low, summaries[b.name].ci_high = lo, hi

    if repeats_out:
        cons = {sid: _consistency(outs) for sid, outs in repeats_out.items()}
        vals = [v for v in cons.values() if v is not None]
        for sid, cv in cons.items():
            if cv is not None:
                results[sid].scores["self_consistency"] = Score(metric="self_consistency", value=cv)
        if vals:
            lo, hi = stats.bootstrap_ci(vals, n_resamples=n_resamples, seed=seed)
            summaries["self_consistency"] = MetricSummary(
                metric="self_consistency",
                family="robustness",
                description=f"Agreement between {repeats} runs of the target on the same input (token F1).",
                n=len(vals),
                value=stats.mean(vals),
                mean=stats.mean(vals),
                median=stats.median(vals),
                std=stats.stdev(vals),
                min=min(vals),
                max=max(vals),
                ci_low=lo,
                ci_high=hi,
            )

    # 3. slices
    slice_out: dict[str, dict[str, MetricSummary]] = {}
    for key in slices or []:
        groups: dict[str, list[Sample]] = {}
        for s in scorable:
            vals_k = (
                s.tags
                if key == "tags"
                else [s.metadata.get(key)]
                if s.metadata.get(key) is not None
                else []
            )
            for gv in vals_k:
                groups.setdefault(f"{key}={gv}", []).append(s)
        for gname, members in sorted(groups.items()):
            gs: dict[str, MetricSummary] = {}
            for b in sample_metrics:
                gs[b.name] = summarize(
                    b,
                    [results[m.id].scores[b.name] for m in members],
                    confidence=confidence,
                    n_resamples=max(200, n_resamples // 4),
                    seed=seed,
                )
            for b in corpus:
                try:
                    co = b.compute(members, ctx)
                    gs[b.name] = summarize(b, [], corpus_value=co.value, corpus_details=co.details)
                except Exception:  # noqa: S112 - a slice too small for a corpus metric is simply left out
                    continue
            slice_out[gname] = gs

    run = RunResult(
        run_id=run_id,
        name=name or ds.name,
        created_at=_now(),
        duration_s=round(time.perf_counter() - started, 3),
        dataset={
            "name": ds.name,
            "source": ds.source,
            "fingerprint": ds.fingerprint,
            "input_fingerprint": ds.input_fingerprint,
            "samples": len(ds),
        },
        target=tgt.describe() if tgt else {},
        metrics=names,
        config={
            "metrics": [
                {
                    "name": b.name,
                    "metric": b.info.name,
                    "params": _jsonable(b.params),
                    "threshold": b.threshold,
                }
                for b in bound
            ],
            "confidence": confidence,
            "n_resamples": n_resamples,
            "seed": seed,
            "repeats": repeats,
            "slices": list(slices or []),
            "embedder": getattr(ctx.embedder, "name", None),
            **(config or {}),
        },
        samples=[results[s.id] for s in samples],
        summaries=summaries,
        slices=slice_out,
        judge=judge_obj.describe() if judge_obj else {},
        environment=environment(root),
    )
    for b in bound:
        sm = summaries.get(b.name)
        if sm is not None and sm.value is None and scorable:
            reasons = {
                sr.scores[b.name].reason
                for sr in run.samples
                if b.name in sr.scores and sr.scores[b.name].reason
            }
            why = next(iter(reasons), "") if len(reasons) == 1 else ""
            run.notes.append(
                f"{b.name} has no value: no sample could be scored" + (f" ({why})" if why else "")
            )
    errored = sum(1 for r in run.samples if r.target_error)
    if errored:
        run.notes.append(
            f"the target failed on {errored} of {len(samples)} samples; they are left out of every metric"
        )

    # 4. gate (Ananke policy engine)
    if gates:
        from guage_kit.harness.convert import gate

        rules = [g if isinstance(g, GateRule) else GateRule.model_validate(g) for g in gates]
        run.config["gates"] = [r.model_dump() for r in rules]
        run.gate = gate(run, rules)

    if save:
        from guage_kit.runner.store import RunStore

        if save is True:
            RunStore(root / ".guage" / "runs").save(run)
        else:
            run.save(Path(save) / "run.json")
    if evidence:
        from guage_kit.harness.convert import write_evidence

        write_evidence(run, root, [GateRule.model_validate(g) for g in run.config.get("gates", [])])
    return run


def _jsonable(params: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in params.items():
        out[k] = list(v) if isinstance(v, tuple) else v
    return out


__all__ = ["auto_metrics", "environment", "evaluate", "summarize"]
