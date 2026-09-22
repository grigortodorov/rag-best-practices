"""Compare retrieval strategies on the same golden cases (stdlib only).

Runs keyword, hybrid, rewrite_hybrid, and hybrid_rerank stubs against a
shared golden set and aggregates hit@k / MRR from :mod:`ragpractices.eval`.
Educational only—not a production A/B harness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ragpractices.eval import GoldenCase, evaluate_retrieval, hit_at_k, mrr
from ragpractices.hybrid import hybrid_search, keyword_score
from ragpractices.rerank import rerank
from ragpractices.rewrite import rewrite_query

STRATEGY_NAMES = (
    "keyword",
    "hybrid",
    "rewrite_hybrid",
    "hybrid_rerank",
)


@dataclass
class StrategyResult:
    """Aggregate metrics for one retrieval strategy."""

    name: str
    hit_at_k_rate: float
    mean_mrr: float
    n_cases: int
    k: int


@dataclass
class CompareReport:
    """Side-by-side strategy comparison with a simple ranking."""

    k: int
    n_cases: int
    strategies: list[StrategyResult] = field(default_factory=list)
    ranking: list[str] = field(default_factory=list)
    notes: str = (
        "Educational strategy compare (hit@k + MRR). "
        "Ranking: higher hit@k, then higher MRR. Not a production A/B test."
    )


def _ids_from_scores(scores: list[float], ids: list[str]) -> list[str]:
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
    return [ids[i] for i in order]


def _normalize_docs(docs: Sequence[str] | Sequence[dict[str, Any]]) -> tuple[list[str], list[str]]:
    texts: list[str] = []
    ids: list[str] = []
    for i, item in enumerate(docs):
        if isinstance(item, str):
            texts.append(item)
            ids.append(f"doc-{i}")
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("document") or "")
            texts.append(text)
            ids.append(str(item.get("id", f"doc-{i}")))
        else:
            raise TypeError(f"doc {i} must be str or dict")
    return texts, ids


def _retrieve_keyword(query: str, texts: list[str], ids: list[str]) -> list[str]:
    scores = keyword_score(query, texts)
    return _ids_from_scores(scores, ids)


def _retrieve_hybrid(query: str, texts: list[str], ids: list[str]) -> list[str]:
    hits = hybrid_search(query, texts, fusion="rrf")
    return [ids[h["index"]] for h in hits]


def _retrieve_rewrite_hybrid(query: str, texts: list[str], ids: list[str]) -> list[str]:
    rewritten = rewrite_query(query, mode="expand")["rewritten"]
    hits = hybrid_search(rewritten, texts, fusion="rrf")
    return [ids[h["index"]] for h in hits]


def _retrieve_hybrid_rerank(query: str, texts: list[str], ids: list[str]) -> list[str]:
    hits = hybrid_search(query, texts, fusion="rrf")
    if not hits:
        return []
    cand_docs = [h["document"] for h in hits]
    cand_ids = [ids[h["index"]] for h in hits]
    ranked = rerank(query, cand_docs)
    return [cand_ids[r["index"]] for r in ranked]


_STRATEGY_FNS: dict[str, Callable[[str, list[str], list[str]], list[str]]] = {
    "keyword": _retrieve_keyword,
    "hybrid": _retrieve_hybrid,
    "rewrite_hybrid": _retrieve_rewrite_hybrid,
    "hybrid_rerank": _retrieve_hybrid_rerank,
}


def compare_strategies(
    cases: Sequence[GoldenCase],
    docs: Sequence[str] | Sequence[dict[str, Any]],
    *,
    k: int = 3,
    strategies: Sequence[str] | None = None,
) -> CompareReport:
    """Run the same golden cases through several retrieval strategies.

    Args:
        cases: Golden cases with queries and expected ids.
        docs: Corpus strings or dicts with ``id`` / ``text``.
        k: hit@k cutoff (default 3).
        strategies: Optional subset of strategy names; default is all four.

    Returns:
        :class:`CompareReport` with per-strategy rates and a ranking
        (higher hit@k first, then higher mean MRR).
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    names = list(strategies) if strategies is not None else list(STRATEGY_NAMES)
    for name in names:
        if name not in _STRATEGY_FNS:
            raise ValueError(
                f"unknown strategy {name!r}; known: {', '.join(STRATEGY_NAMES)}"
            )

    texts, ids = _normalize_docs(docs)
    results: list[StrategyResult] = []
    for name in names:
        fn = _STRATEGY_FNS[name]

        def retrieve_fn(query: str, _fn=fn) -> list[str]:
            return _fn(query, texts, ids)

        report = evaluate_retrieval(cases, retrieve_fn, k=k)
        results.append(
            StrategyResult(
                name=name,
                hit_at_k_rate=report.hit_at_k_rate,
                mean_mrr=report.mean_mrr,
                n_cases=report.n_cases,
                k=k,
            )
        )

    ranking = sorted(
        results,
        key=lambda s: (-s.hit_at_k_rate, -s.mean_mrr, s.name),
    )
    return CompareReport(
        k=k,
        n_cases=len(cases),
        strategies=results,
        ranking=[s.name for s in ranking],
    )


def report_to_dict(report: CompareReport) -> dict[str, Any]:
    """Serialize a :class:`CompareReport` to a JSON-friendly dict."""
    return {
        "k": report.k,
        "n_cases": report.n_cases,
        "ranking": list(report.ranking),
        "notes": report.notes,
        "strategies": [
            {
                "name": s.name,
                "hit_at_k_rate": s.hit_at_k_rate,
                "mean_mrr": s.mean_mrr,
                "n_cases": s.n_cases,
                "k": s.k,
            }
            for s in report.strategies
        ],
    }


def format_compare_table(report: CompareReport) -> str:
    """Plain-text table of strategy metrics plus ranking."""
    rows = report.strategies
    if not rows:
        return "n_cases: 0\n(no strategies)\n"
    name_w = max(len("strategy"), max(len(s.name) for s in rows))
    hit_label = f"hit@{report.k}"
    lines = [
        f"n_cases: {report.n_cases}  k: {report.k}",
        f"{'strategy':<{name_w}}  {hit_label:>8}  {'mean_mrr':>8}",
        f"{'-' * name_w}  {'-' * 8}  {'-' * 8}",
    ]
    for s in rows:
        lines.append(
            f"{s.name:<{name_w}}  {s.hit_at_k_rate:8.4f}  {s.mean_mrr:8.4f}"
        )
    lines.append("")
    lines.append(f"ranking: {' > '.join(report.ranking)}")
    lines.append(f"notes: {report.notes}")
    return "\n".join(lines) + "\n"


# Re-export metrics used by callers that import from compare
__all__ = [
    "STRATEGY_NAMES",
    "CompareReport",
    "StrategyResult",
    "compare_strategies",
    "format_compare_table",
    "report_to_dict",
    "hit_at_k",
    "mrr",
]
