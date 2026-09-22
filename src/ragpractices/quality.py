"""Chunk quality stats and near-duplicate detection (stdlib only).

Helpers for inspecting chunk length distributions and dropping near-duplicate
chunks via token Jaccard similarity. Educational—not a full dedupe pipeline.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from typing import Any

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.casefold()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


@dataclass
class ChunkStats:
    """Length statistics over a list of chunk texts."""

    n: int
    mean_length: float
    median_length: float
    min_length: int
    max_length: int
    empty_count: int
    very_short_count: int
    very_short_threshold: int = 20


@dataclass
class ChunkIssue:
    """A flagged quality issue for one chunk."""

    index: int
    kind: str
    detail: str
    length: int


@dataclass
class DedupeResult:
    """Result of near-duplicate filtering via token Jaccard."""

    kept_indices: list[int]
    dropped_pairs: list[tuple[int, int, float]] = field(default_factory=list)
    threshold: float = 0.9


def chunk_stats(texts: list[str], *, very_short: int = 20) -> ChunkStats:
    """Compute length stats for chunk texts.

    ``very_short`` counts chunks with ``0 < len < very_short`` (empty counted
    separately). Empty input yields zeros.
    """
    if very_short < 0:
        raise ValueError("very_short must be >= 0")
    lengths = [len(t) for t in texts]
    n = len(lengths)
    if n == 0:
        return ChunkStats(
            n=0,
            mean_length=0.0,
            median_length=0.0,
            min_length=0,
            max_length=0,
            empty_count=0,
            very_short_count=0,
            very_short_threshold=very_short,
        )
    empty = sum(1 for L in lengths if L == 0)
    short = sum(1 for L in lengths if 0 < L < very_short)
    return ChunkStats(
        n=n,
        mean_length=float(statistics.mean(lengths)),
        median_length=float(statistics.median(lengths)),
        min_length=min(lengths),
        max_length=max(lengths),
        empty_count=empty,
        very_short_count=short,
        very_short_threshold=very_short,
    )


def flag_chunks(
    texts: list[str],
    *,
    min_chars: int = 20,
    max_chars: int = 4000,
) -> list[ChunkIssue]:
    """Flag empty, too-short, and too-long chunks.

    Returns a list of :class:`ChunkIssue` (may be empty). Raises if
    ``min_chars < 0`` or ``max_chars < min_chars``.
    """
    if min_chars < 0:
        raise ValueError("min_chars must be >= 0")
    if max_chars < min_chars:
        raise ValueError("max_chars must be >= min_chars")
    issues: list[ChunkIssue] = []
    for i, text in enumerate(texts):
        L = len(text)
        if L == 0:
            issues.append(
                ChunkIssue(index=i, kind="empty", detail="chunk is empty", length=0)
            )
        elif L < min_chars:
            issues.append(
                ChunkIssue(
                    index=i,
                    kind="too_short",
                    detail=f"length {L} < min_chars {min_chars}",
                    length=L,
                )
            )
        elif L > max_chars:
            issues.append(
                ChunkIssue(
                    index=i,
                    kind="too_long",
                    detail=f"length {L} > max_chars {max_chars}",
                    length=L,
                )
            )
    return issues


def dedupe_near(
    texts: list[str],
    *,
    threshold: float = 0.9,
) -> DedupeResult:
    """Keep first occurrence; drop later chunks with Jaccard >= ``threshold``.

    Tokenization is casefold + alphanumeric (same spirit as hybrid keyword
    scoring). ``threshold`` must be in ``[0, 1]``.

    Returns kept indices (stable order) and dropped pairs
    ``(kept_index, dropped_index, jaccard)``.
    """
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [0, 1]")
    token_sets = [_tokenize(t) for t in texts]
    kept: list[int] = []
    dropped: list[tuple[int, int, float]] = []
    for i, toks in enumerate(token_sets):
        dup_of: int | None = None
        best_sim = 0.0
        for j in kept:
            sim = _jaccard(toks, token_sets[j])
            if sim >= threshold and sim >= best_sim:
                dup_of = j
                best_sim = sim
        if dup_of is not None:
            dropped.append((dup_of, i, best_sim))
        else:
            kept.append(i)
    return DedupeResult(kept_indices=kept, dropped_pairs=dropped, threshold=threshold)


def stats_to_dict(stats: ChunkStats) -> dict[str, Any]:
    """JSON-friendly dict for :class:`ChunkStats`."""
    return {
        "n": stats.n,
        "mean_length": stats.mean_length,
        "median_length": stats.median_length,
        "min_length": stats.min_length,
        "max_length": stats.max_length,
        "empty_count": stats.empty_count,
        "very_short_count": stats.very_short_count,
        "very_short_threshold": stats.very_short_threshold,
    }
