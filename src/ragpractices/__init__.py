"""ragpractices — small helpers for RAG chunking, rubrics, and checklists."""

from ragpractices.checklist import get_checklist
from ragpractices.chunking import chunk_by_headings, chunk_text
from ragpractices.rubric import (
    DIMENSIONS,
    format_scorecard,
    score_answer,
)

__version__ = "0.1.0"

__all__ = [
    "DIMENSIONS",
    "__version__",
    "chunk_by_headings",
    "chunk_text",
    "format_scorecard",
    "get_checklist",
    "score_answer",
]
