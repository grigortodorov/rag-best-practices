"""Hybrid (sparse + dense) search stubs (stdlib only).

Provides a deterministic BM25-lite keyword scorer, min-max normalization,
reciprocal rank fusion (RRF), and a small hybrid_search helper that can fuse
keyword and dense ranks via RRF or a weighted sum of normalized scores.
"""

from __future__ import annotations

import math
import re
from typing import Any, Literal

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokenize(text: str) -> list[str]:
    """Casefold and split into alphanumeric tokens."""
    return _TOKEN_RE.findall(text.casefold())


def keyword_score(query: str, documents: list[str]) -> list[float]:
    """BM25-lite keyword overlap scores (document TF * IDF-ish).

    Tokenization is casefold + alphanumeric. IDF for term ``t`` is
    ``log((N + 1) / (df(t) + 1)) + 1`` where ``N`` is the corpus size.
    Document score is the sum over query terms of ``tf * idf`` (raw term
    frequency in the document; query term multiplicity is ignored).

    Deterministic for a given ``(query, documents)`` pair.

    Args:
        query: Free-text query.
        documents: Corpus strings (may be empty).

    Returns:
        One float score per document (same order). Empty corpus → ``[]``.
    """
    if not documents:
        return []

    query_terms = list(dict.fromkeys(_tokenize(query)))  # unique, stable order
    if not query_terms:
        return [0.0] * len(documents)

    n = len(documents)
    tokenized = [_tokenize(doc) for doc in documents]

    df: dict[str, int] = {t: 0 for t in query_terms}
    for tokens in tokenized:
        present = set(tokens)
        for t in query_terms:
            if t in present:
                df[t] += 1

    idf = {t: math.log((n + 1) / (df[t] + 1)) + 1.0 for t in query_terms}

    scores: list[float] = []
    for tokens in tokenized:
        tf: dict[str, int] = {}
        for tok in tokens:
            if tok in idf:
                tf[tok] = tf.get(tok, 0) + 1
        score = 0.0
        for t in query_terms:
            score += tf.get(t, 0) * idf[t]
        scores.append(score)

    return scores


def normalize_scores(scores: list[float]) -> list[float]:
    """Min-max normalize scores to ``[0, 1]``.

    Empty input returns ``[]``. Constant (including all-zero) inputs return
    a list of zeros of the same length so downstream fusion stays defined.
    """
    if not scores:
        return []
    lo = min(scores)
    hi = max(scores)
    if hi == lo:
        return [0.0] * len(scores)
    span = hi - lo
    return [(s - lo) / span for s in scores]


def reciprocal_rank_fusion(
    rank_lists: list[list[int]], k: int = 60
) -> list[tuple[int, float]]:
    """Reciprocal Rank Fusion over ranked document index lists.

    Each ``rank_lists[i]`` is a permutation (or prefix) of document indices
    with the best match first. Score for document ``d`` is
    ``sum_i 1 / (k + rank_i(d))`` where ``rank_i`` is 1-based. Documents
    missing from a list contribute nothing from that list.

    Args:
        rank_lists: One or more ranked index lists.
        k: RRF smoothing constant (must be > 0).

    Returns:
        ``(doc_index, score)`` pairs sorted by score descending, then index
        ascending for ties.
    """
    if k <= 0:
        raise ValueError("k must be > 0")

    fused: dict[int, float] = {}
    for ranks in rank_lists:
        for rank_pos, doc_index in enumerate(ranks, start=1):
            fused[doc_index] = fused.get(doc_index, 0.0) + 1.0 / (k + rank_pos)

    return sorted(fused.items(), key=lambda item: (-item[1], item[0]))


def _ranks_from_scores(scores: list[float]) -> list[int]:
    """Return document indices sorted by score descending (index asc on ties)."""
    indexed = list(enumerate(scores))
    indexed.sort(key=lambda item: (-item[1], item[0]))
    return [i for i, _ in indexed]


FusionMode = Literal["rrf", "weighted"]


def hybrid_search(
    query: str,
    documents: list[str],
    dense_scores: list[float] | None = None,
    *,
    rrf_k: int = 60,
    alpha: float = 0.5,
    fusion: FusionMode = "rrf",
) -> list[dict[str, Any]]:
    """Fuse keyword (sparse) and optional dense scores into a ranked list.

    Sparse scores come from :func:`keyword_score`. If ``dense_scores`` is
    ``None``, zeros are used (keyword-only path). If provided, length must
    match ``documents``.

    Fusion modes:

    - ``"rrf"``: :func:`reciprocal_rank_fusion` over sparse and dense ranks
      (``rrf_k`` smoothing).
    - ``"weighted"``: ``alpha * norm(dense) + (1 - alpha) * norm(sparse)``.

    Args:
        query: Free-text query for the sparse scorer.
        documents: Corpus strings.
        dense_scores: Optional per-document dense similarity scores.
        rrf_k: RRF ``k`` (ignored for weighted fusion).
        alpha: Dense weight in ``[0, 1]`` for weighted fusion.
        fusion: ``"rrf"`` or ``"weighted"``.

    Returns:
        List of ``{"index", "score", "document"}`` dicts, best first.
    """
    if fusion not in ("rrf", "weighted"):
        raise ValueError("fusion must be 'rrf' or 'weighted'")
    if not 0.0 <= alpha <= 1.0:
        raise ValueError("alpha must be in [0, 1]")

    n = len(documents)
    if dense_scores is None:
        dense = [0.0] * n
    else:
        if len(dense_scores) != n:
            raise ValueError(
                f"dense_scores length {len(dense_scores)} != documents length {n}"
            )
        dense = list(dense_scores)

    if n == 0:
        return []

    sparse = keyword_score(query, documents)

    if fusion == "rrf":
        sparse_ranks = _ranks_from_scores(sparse)
        dense_ranks = _ranks_from_scores(dense)
        fused = reciprocal_rank_fusion([sparse_ranks, dense_ranks], k=rrf_k)
        results = [
            {"index": idx, "score": score, "document": documents[idx]}
            for idx, score in fused
        ]
    else:
        norm_dense = normalize_scores(dense)
        norm_sparse = normalize_scores(sparse)
        combined = [
            alpha * norm_dense[i] + (1.0 - alpha) * norm_sparse[i] for i in range(n)
        ]
        order = _ranks_from_scores(combined)
        results = [
            {"index": idx, "score": combined[idx], "document": documents[idx]}
            for idx in order
        ]

    return results
