"""Offline retrieval evaluation helpers (stdlib only).

Educational metrics for ranking quality against a small golden set:
hit@k and mean reciprocal rank (MRR). These are **not** a substitute for
human judgment, production relevance labels, or online A/B metrics—use them
to catch regressions in keyword/hybrid stubs during local iteration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence


@dataclass
class GoldenCase:
    """One offline retrieval case: a query and the doc ids that should rank."""

    query: str
    expected_ids: list[str]
    id: str = ""

    @classmethod
    def from_dict(cls, obj: dict[str, Any], *, index: int = 0) -> GoldenCase:
        if not isinstance(obj, dict):
            raise ValueError(f"golden case {index} must be an object")
        query = obj.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"golden case {index} needs a non-empty query string")
        raw_ids = obj.get("expected_ids") or obj.get("expected") or []
        if not isinstance(raw_ids, list):
            raise ValueError(f"golden case {index}: expected_ids must be a list")
        expected = [str(x) for x in raw_ids]
        case_id = str(obj.get("id") or f"case-{index}")
        return cls(query=query.strip(), expected_ids=expected, id=case_id)


@dataclass
class CaseResult:
    """Per-case retrieval eval detail."""

    case_id: str
    query: str
    retrieved_ids: list[str]
    expected_ids: list[str]
    hit_at_k: bool
    mrr: float
    k: int


@dataclass
class EvalReport:
    """Aggregate offline retrieval evaluation report."""

    n_cases: int
    hit_at_k_rate: float
    mean_mrr: float
    k: int
    cases: list[CaseResult] = field(default_factory=list)
    notes: str = (
        "Educational offline retrieval eval (hit@k + MRR). "
        "Not a substitute for human judgment or production metrics."
    )


def hit_at_k(
    retrieved_ids: Sequence[str],
    expected_ids: Sequence[str],
    k: int,
) -> bool:
    """True if any expected id appears in the top-``k`` retrieved ids.

    ``k`` must be >= 1. Empty ``expected_ids`` always yields ``False``.
    Comparison is exact string match on ids.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    if not expected_ids:
        return False
    top = list(retrieved_ids)[:k]
    expected = set(expected_ids)
    return any(rid in expected for rid in top)


def mrr(retrieved_ids: Sequence[str], expected_ids: Sequence[str]) -> float:
    """Mean reciprocal rank of the first hit among ``expected_ids``.

    Returns ``1/rank`` for the first retrieved id that is expected (1-based),
    or ``0.0`` if none match / expected is empty.
    """
    if not expected_ids:
        return 0.0
    expected = set(expected_ids)
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in expected:
            return 1.0 / float(rank)
    return 0.0


def evaluate_retrieval(
    cases: Sequence[GoldenCase],
    retrieve_fn: Callable[[str], Sequence[str]],
    *,
    k: int = 5,
) -> EvalReport:
    """Run ``retrieve_fn`` on each golden case and aggregate hit@k + MRR.

    ``retrieve_fn(query)`` must return ordered document ids (best first).

    Args:
        cases: Golden cases with queries and expected ids.
        retrieve_fn: Callable mapping query → ranked id list.
        k: Cutoff for hit@k (default 5).

    Returns:
        :class:`EvalReport` with rates and per-case details.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    details: list[CaseResult] = []
    hits = 0
    mrr_sum = 0.0
    for case in cases:
        retrieved = list(retrieve_fn(case.query))
        h = hit_at_k(retrieved, case.expected_ids, k)
        r = mrr(retrieved, case.expected_ids)
        if h:
            hits += 1
        mrr_sum += r
        details.append(
            CaseResult(
                case_id=case.id,
                query=case.query,
                retrieved_ids=retrieved,
                expected_ids=list(case.expected_ids),
                hit_at_k=h,
                mrr=r,
                k=k,
            )
        )
    n = len(cases)
    return EvalReport(
        n_cases=n,
        hit_at_k_rate=(hits / n) if n else 0.0,
        mean_mrr=(mrr_sum / n) if n else 0.0,
        k=k,
        cases=details,
    )


def load_golden_jsonl(path: str | Path) -> list[GoldenCase]:
    """Load golden cases from a JSONL file (one object per line)."""
    text = Path(path).read_text(encoding="utf-8")
    cases: list[GoldenCase] = []
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        cases.append(GoldenCase.from_dict(obj, index=i))
    return cases


def report_to_dict(report: EvalReport) -> dict[str, Any]:
    """Serialize an :class:`EvalReport` to a JSON-friendly dict."""
    return {
        "n_cases": report.n_cases,
        "hit_at_k_rate": report.hit_at_k_rate,
        "mean_mrr": report.mean_mrr,
        "k": report.k,
        "notes": report.notes,
        "cases": [
            {
                "case_id": c.case_id,
                "query": c.query,
                "retrieved_ids": c.retrieved_ids,
                "expected_ids": c.expected_ids,
                "hit_at_k": c.hit_at_k,
                "mrr": c.mrr,
                "k": c.k,
            }
            for c in report.cases
        ],
    }
