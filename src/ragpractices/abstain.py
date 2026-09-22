"""Fail-closed answer / abstain / clarify decision helper (stdlib only).

Educational gate for RAG demos: when retrieval is empty or scores are below
thresholds, prefer abstaining or asking for clarification instead of inventing
a confident answer. Thresholds are illustrative—tune them for your product.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Decision = Literal["answer", "abstain", "clarify"]


@dataclass
class AbstainResult:
    """Outcome of a fail-closed answer gate."""

    decision: Decision
    reason: str


def should_answer(
    *,
    top_score: float | None = None,
    groundedness: float | None = None,
    min_top_score: float = 0.1,
    min_groundedness: float = 0.3,
    empty_retrieval: bool = False,
) -> AbstainResult:
    """Decide whether to answer, abstain, or ask for clarification.

    Priority (fail closed):

    1. ``empty_retrieval`` → ``abstain``
    2. ``top_score`` provided and below ``min_top_score`` → ``abstain``
    3. ``groundedness`` provided and below ``min_groundedness`` → ``clarify``
       (some retrieval signal, but answer may not be well supported)
    4. Otherwise → ``answer``

    Missing optional scores are treated as "not checked" (do not block).
    """
    if empty_retrieval:
        return AbstainResult(
            decision="abstain",
            reason="empty retrieval: no documents to ground an answer",
        )

    if top_score is not None and top_score < min_top_score:
        return AbstainResult(
            decision="abstain",
            reason=(
                f"top retrieval score {top_score:.4f} is below "
                f"min_top_score {min_top_score:.4f}"
            ),
        )

    if groundedness is not None and groundedness < min_groundedness:
        return AbstainResult(
            decision="clarify",
            reason=(
                f"groundedness {groundedness:.4f} is below "
                f"min_groundedness {min_groundedness:.4f}; "
                "ask a clarifying question or request better sources"
            ),
        )

    parts: list[str] = []
    if top_score is not None:
        parts.append(f"top_score={top_score:.4f}>={min_top_score:.4f}")
    if groundedness is not None:
        parts.append(f"groundedness={groundedness:.4f}>={min_groundedness:.4f}")
    if not parts:
        parts.append("no blocking signals (scores unchecked)")
    return AbstainResult(
        decision="answer",
        reason="ok to answer: " + ", ".join(parts),
    )
