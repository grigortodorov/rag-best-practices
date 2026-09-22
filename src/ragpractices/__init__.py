"""ragpractices — small helpers for RAG chunking, rubrics, checklists, hybrid search, and ingest."""

from ragpractices.checklist import get_checklist
from ragpractices.chunking import chunk_by_headings, chunk_text
from ragpractices.citations import (
    Citation,
    attach_citations,
    build_sources_block,
    format_inline_citations,
)
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
from ragpractices.rerank import mmr_rerank, rerank
from ragpractices.rewrite import multi_query, rewrite_query
from ragpractices.rubric import (
    DIMENSIONS,
    format_scorecard,
    score_answer,
)

__version__ = "0.4.0"

__all__ = [
    "DIMENSIONS",
    "Citation",
    "Document",
    "__version__",
    "attach_citations",
    "build_sources_block",
    "chunk_by_headings",
    "chunk_text",
    "corpus_to_hybrid_docs",
    "format_inline_citations",
    "format_scorecard",
    "get_checklist",
    "hybrid_search",
    "keyword_score",
    "load_corpus_jsonl",
    "load_markdown_file",
    "load_path",
    "load_text_file",
    "mmr_rerank",
    "multi_query",
    "normalize_scores",
    "reciprocal_rank_fusion",
    "rerank",
    "rewrite_query",
    "save_corpus_jsonl",
    "score_answer",
]
