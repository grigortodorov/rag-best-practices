"""ragpractices — small helpers for RAG chunking, rubrics, checklists, and hybrid search."""

from ragpractices.checklist import get_checklist
from ragpractices.chunking import chunk_by_headings, chunk_text
from ragpractices.hybrid import (
    hybrid_search,
    keyword_score,
    normalize_scores,
    reciprocal_rank_fusion,
)
from ragpractices.rubric import (
    DIMENSIONS,
    format_scorecard,
    score_answer,
)

__version__ = "0.2.0"

__all__ = [
    "DIMENSIONS",
    "__version__",
    "chunk_by_headings",
    "chunk_text",
    "format_scorecard",
    "get_checklist",
    "hybrid_search",
    "keyword_score",
    "normalize_scores",
    "reciprocal_rank_fusion",
    "score_answer",
]
