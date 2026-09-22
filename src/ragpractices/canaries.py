"""Index canary probes for retrieval regression checks (stdlib only).

A canary is a query + expected document ids (optionally scoped by tags /
tenant / roles). Run canaries against a corpus with hybrid (or keyword)
retrieval; fail the probe when expected ids miss top-k. Useful as a CI
smoke gate after index or filter changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from ragpractices.eval import hit_at_k, mrr
from ragpractices.filters import filter_docs
from ragpractices.hybrid import hybrid_search, keyword_score


@dataclass
class Canary:
    """One index canary probe."""

    query: str
    expected_ids: list[str]
    id: str = ""
    tags: list[str] = field(default_factory=list)
    tenant: str | None = None
    roles: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, obj: dict[str, Any], *, index: int = 0) -> Canary:
        if not isinstance(obj, dict):
            raise ValueError(f"canary {index} must be an object")
        query = obj.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"canary {index} needs a non-empty query string")
        raw_ids = obj.get("expected_ids") or obj.get("expected") or []
        if not isinstance(raw_ids, list):
            raise ValueError(f"canary {index}: expected_ids must be a list")
        tags = obj.get("tags") or []
        roles = obj.get("roles") or []
        if isinstance(tags, str):
            tags = [tags]
        if isinstance(roles, str):
            roles = [roles]
        tenant = obj.get("tenant")
        if tenant is not None:
            tenant = str(tenant)
        return cls(
            query=query.strip(),
            expected_ids=[str(x) for x in raw_ids],
            id=str(obj.get("id") or f"canary-{index}"),
            tags=[str(t) for t in tags],
            tenant=tenant,
            roles=[str(r) for r in roles],
        )


@dataclass
class CanaryResult:
    """Per-canary pass/fail detail."""

    canary_id: str
    query: str
    retrieved_ids: list[str]
    expected_ids: list[str]
    passed: bool
    hit_at_k: bool
    mrr: float
    k: int
    filtered_n: int = 0


@dataclass
class CanaryReport:
    """Aggregate canary run report."""

    n_canaries: int
    n_passed: int
    n_failed: int
    k: int
    all_passed: bool
    results: list[CanaryResult] = field(default_factory=list)
    notes: str = (
        "Educational index canaries (hit@k gate). "
        "Exit non-zero in CI when any probe fails."
    )


def _normalize_docs(
    docs: Sequence[str | dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, item in enumerate(docs):
        if isinstance(item, str):
            out.append({"id": f"doc-{i}", "text": item})
        elif isinstance(item, dict):
            row = dict(item)
            if "id" not in row:
                row["id"] = f"doc-{i}"
            if "text" not in row and "document" in row:
                row["text"] = row["document"]
            out.append(row)
        else:
            raise TypeError(f"doc {i} must be str or dict")
    return out


def _retrieve_hybrid(query: str, texts: list[str], ids: list[str]) -> list[str]:
    hits = hybrid_search(query, texts, fusion="rrf")
    return [ids[h["index"]] for h in hits]


def _retrieve_keyword(query: str, texts: list[str], ids: list[str]) -> list[str]:
    scores = keyword_score(query, texts)
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
    return [ids[i] for i in order]


RetrieveFn = Callable[[str, list[str], list[str]], list[str]]

_RETRIEVE_MODES: dict[str, RetrieveFn] = {
    "hybrid": _retrieve_hybrid,
    "keyword": _retrieve_keyword,
}


def run_canaries(
    canaries: Sequence[Canary],
    docs: Sequence[str | dict[str, Any]],
    *,
    k: int = 3,
    retrieve: str | RetrieveFn = "hybrid",
) -> CanaryReport:
    """Run canary probes; pass when any expected id appears in top-``k``.

    Optional per-canary ``tags`` / ``tenant`` / ``roles`` filter the corpus
    via :func:`filter_docs` before retrieval (fail-closed ACL).

    Args:
        canaries: Probe definitions.
        docs: Corpus strings or dicts (``id``, ``text``, optional ACL fields).
        k: hit@k cutoff (default 3).
        retrieve: ``"hybrid"``, ``"keyword"``, or a custom
            ``(query, texts, ids) -> ranked_ids`` callable.

    Returns:
        :class:`CanaryReport` with per-probe results and ``all_passed``.
    """
    if k < 1:
        raise ValueError("k must be >= 1")

    if isinstance(retrieve, str):
        if retrieve not in _RETRIEVE_MODES:
            raise ValueError(
                f"unknown retrieve mode {retrieve!r}; known: "
                f"{', '.join(_RETRIEVE_MODES)}"
            )
        retrieve_fn = _RETRIEVE_MODES[retrieve]
    else:
        retrieve_fn = retrieve

    corpus = _normalize_docs(docs)
    results: list[CanaryResult] = []
    n_passed = 0

    for canary in canaries:
        filtered = filter_docs(
            corpus,
            tags=canary.tags or None,
            tenant=canary.tenant,
            roles=canary.roles or None,
        )
        texts = [str(d.get("text") or "") for d in filtered]
        ids = [str(d.get("id")) for d in filtered]
        ranked = retrieve_fn(canary.query, texts, ids) if texts else []
        top = ranked[:k]
        h = hit_at_k(ranked, canary.expected_ids, k)
        r = mrr(ranked, canary.expected_ids)
        passed = h
        if passed:
            n_passed += 1
        results.append(
            CanaryResult(
                canary_id=canary.id,
                query=canary.query,
                retrieved_ids=list(top),
                expected_ids=list(canary.expected_ids),
                passed=passed,
                hit_at_k=h,
                mrr=r,
                k=k,
                filtered_n=len(filtered),
            )
        )

    n = len(canaries)
    n_failed = n - n_passed
    return CanaryReport(
        n_canaries=n,
        n_passed=n_passed,
        n_failed=n_failed,
        k=k,
        all_passed=(n_failed == 0 and n > 0) or n == 0,
        results=results,
    )


def load_canaries_jsonl(path: str | Path) -> list[Canary]:
    """Load canaries from a JSONL file (one object per line)."""
    text = Path(path).read_text(encoding="utf-8")
    canaries: list[Canary] = []
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        canaries.append(Canary.from_dict(obj, index=i))
    return canaries


def report_to_dict(report: CanaryReport) -> dict[str, Any]:
    """Serialize a :class:`CanaryReport` to a JSON-friendly dict."""
    return {
        "n_canaries": report.n_canaries,
        "n_passed": report.n_passed,
        "n_failed": report.n_failed,
        "k": report.k,
        "all_passed": report.all_passed,
        "notes": report.notes,
        "results": [
            {
                "canary_id": r.canary_id,
                "query": r.query,
                "retrieved_ids": r.retrieved_ids,
                "expected_ids": r.expected_ids,
                "passed": r.passed,
                "hit_at_k": r.hit_at_k,
                "mrr": r.mrr,
                "k": r.k,
                "filtered_n": r.filtered_n,
            }
            for r in report.results
        ],
    }


def format_canary_report(report: CanaryReport) -> str:
    """Human-readable canary summary."""
    status = "PASS" if report.all_passed else "FAIL"
    lines = [
        f"canaries: {report.n_passed}/{report.n_canaries} passed  k={report.k}  [{status}]",
    ]
    for r in report.results:
        mark = "ok" if r.passed else "FAIL"
        lines.append(
            f"  [{mark}] {r.canary_id}: hit={r.hit_at_k} mrr={r.mrr:.4f} "
            f"got={r.retrieved_ids} expect={r.expected_ids}"
        )
    lines.append(f"notes: {report.notes}")
    return "\n".join(lines) + "\n"


__all__ = [
    "Canary",
    "CanaryReport",
    "CanaryResult",
    "format_canary_report",
    "load_canaries_jsonl",
    "report_to_dict",
    "run_canaries",
]
