"""Rerank stubs: keyword-overlap blend and simple MMR (stdlib only)."""

from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.casefold())


def _token_set(text: str) -> set[str]:
    return set(_tokenize(text))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _normalize(scores: list[float]) -> list[float]:
    if not scores:
        return []
    lo = min(scores)
    hi = max(scores)
    if hi == lo:
        return [0.0] * len(scores)
    span = hi - lo
    return [(s - lo) / span for s in scores]


def _keyword_overlap(query: str, document: str) -> float:
    """Fraction of unique query tokens found in the document."""
    q = _token_set(query)
    if not q:
        return 0.0
    d = _token_set(document)
    return len(q & d) / len(q)


def rerank(
    query: str,
    documents: list[str],
    *,
    scores: list[float] | None = None,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Rerank documents by blended keyword overlap (+ optional scores).

    Final score = ``0.5 * norm(keyword_overlap) + 0.5 * norm(incoming)``
    when ``scores`` is provided; otherwise pure normalized keyword overlap.

    Args:
        query: Free-text query.
        documents: Candidate strings (corpus or retrieval hits).
        scores: Optional prior scores (same length as ``documents``).
        top_k: If set, return only the top ``k`` results.

    Returns:
        ``{"index", "score", "document"}`` dicts sorted score descending,
        then index ascending on ties.
    """
    n = len(documents)
    if scores is not None and len(scores) != n:
        raise ValueError(
            f"scores length {len(scores)} != documents length {n}"
        )
    if top_k is not None and top_k < 0:
        raise ValueError("top_k must be >= 0")

    if n == 0:
        return []

    overlaps = [_keyword_overlap(query, doc) for doc in documents]
    norm_overlap = _normalize(overlaps)

    if scores is None:
        blended = list(norm_overlap)
    else:
        norm_in = _normalize([float(s) for s in scores])
        blended = [
            0.5 * norm_overlap[i] + 0.5 * norm_in[i] for i in range(n)
        ]

    order = sorted(range(n), key=lambda i: (-blended[i], i))
    results = [
        {"index": i, "score": blended[i], "document": documents[i]}
        for i in order
    ]
    if top_k is not None:
        results = results[:top_k]
    return results


def mmr_rerank(
    query: str,
    documents: list[str],
    *,
    lambda_mult: float = 0.7,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Maximal Marginal Relevance rerank using token Jaccard similarity.

    Relevance to the query and redundancy vs already-selected docs both use
    Jaccard over casefolded alphanumeric token sets. Deterministic.

    Score at each step::

        λ * sim(query, doc) - (1 - λ) * max_{s in selected} sim(doc, s)

    Args:
        query: Free-text query.
        documents: Candidate strings.
        lambda_mult: Tradeoff in ``[0, 1]`` (higher → more relevance).
        top_k: Maximum results to return.

    Returns:
        ``{"index", "score", "document"}`` in MMR selection order.
    """
    if not 0.0 <= lambda_mult <= 1.0:
        raise ValueError("lambda_mult must be in [0, 1]")
    if top_k < 0:
        raise ValueError("top_k must be >= 0")

    n = len(documents)
    if n == 0 or top_k == 0:
        return []

    q_set = _token_set(query)
    doc_sets = [_token_set(d) for d in documents]
    rel = [_jaccard(q_set, ds) for ds in doc_sets]

    selected: list[int] = []
    selected_sets: list[set[str]] = []
    results: list[dict[str, Any]] = []
    remaining = set(range(n))
    k = min(top_k, n)

    while len(selected) < k and remaining:
        best_i = -1
        best_score = float("-inf")
        for i in sorted(remaining):  # stable tie-break by index
            if not selected_sets:
                mmr = lambda_mult * rel[i]
            else:
                max_sim = max(_jaccard(doc_sets[i], s) for s in selected_sets)
                mmr = lambda_mult * rel[i] - (1.0 - lambda_mult) * max_sim
            if mmr > best_score or (mmr == best_score and (best_i < 0 or i < best_i)):
                best_score = mmr
                best_i = i
        selected.append(best_i)
        selected_sets.append(doc_sets[best_i])
        remaining.remove(best_i)
        results.append(
            {
                "index": best_i,
                "score": best_score,
                "document": documents[best_i],
            }
        )

    return results
