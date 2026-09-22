"""ragpractices — small helpers for RAG chunking, rubrics, checklists, hybrid search, and ingest."""

from ragpractices.checklist import get_checklist
from ragpractices.chunking import chunk_by_headings, chunk_text
from ragpractices.hybrid import (
    hybrid_search,
    keyword_score,
    normalize_scores,
    reciprocal_rank_fusion,
)
from ragpractices.ingest import (
    Document,
    corpus_to_hybrid_docs,
    load_corpus_jsonl,
    load_markdown_file,
    load_path,
    load_text_file,
    save_corpus_jsonl,
)
from ragpractices.rubric import (
    DIMENSIONS,
    format_scorecard,
    score_answer,
)

__version__ = "0.3.0"

__all__ = [
    "DIMENSIONS",
    "Document",
    "__version__",
    "chunk_by_headings",
    "chunk_text",
    "corpus_to_hybrid_docs",
    "format_scorecard",
    "get_checklist",
    "hybrid_search",
    "keyword_score",
    "load_corpus_jsonl",
    "load_markdown_file",
    "load_path",
    "load_text_file",
    "normalize_scores",
    "reciprocal_rank_fusion",
    "save_corpus_jsonl",
    "score_answer",
]
