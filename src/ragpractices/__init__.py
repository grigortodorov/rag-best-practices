"""ragpractices — small helpers for RAG chunking, rubrics, checklists, hybrid search, and ingest."""

from ragpractices.abstain import AbstainResult, Decision, should_answer
from ragpractices.checklist import get_checklist
from ragpractices.chunking import chunk_by_headings, chunk_text
from ragpractices.citations import (
    Citation,
    attach_citations,
    build_sources_block,
    format_inline_citations,
)
from ragpractices.eval import (
    CaseResult,
    EvalReport,
    GoldenCase,
    evaluate_retrieval,
    hit_at_k,
    load_golden_jsonl,
    mrr,
)
from ragpractices.groundedness import GroundednessReport, check_groundedness
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
from ragpractices.packing import PackResult, estimate_tokens, pack_context, truncate_to_tokens
from ragpractices.pipeline import (
    PipelineResult,
    StageTrace,
    load_pipeline_config,
    run_pipeline,
)
from ragpractices.quality import (
    ChunkIssue,
    ChunkStats,
    DedupeResult,
    chunk_stats,
    dedupe_near,
    flag_chunks,
)
from ragpractices.rerank import mmr_rerank, rerank
from ragpractices.rewrite import multi_query, rewrite_query
from ragpractices.rubric import (
    DIMENSIONS,
    format_scorecard,
    score_answer,
)

__version__ = "0.6.0"

__all__ = [
    "DIMENSIONS",
    "AbstainResult",
    "CaseResult",
    "ChunkIssue",
    "ChunkStats",
    "Citation",
    "Decision",
    "DedupeResult",
    "Document",
    "EvalReport",
    "GoldenCase",
    "GroundednessReport",
    "PackResult",
    "PipelineResult",
    "StageTrace",
    "__version__",
    "attach_citations",
    "build_sources_block",
    "check_groundedness",
    "chunk_by_headings",
    "chunk_stats",
    "chunk_text",
    "corpus_to_hybrid_docs",
    "dedupe_near",
    "estimate_tokens",
    "evaluate_retrieval",
    "flag_chunks",
    "format_inline_citations",
    "format_scorecard",
    "get_checklist",
    "hit_at_k",
    "hybrid_search",
    "keyword_score",
    "load_corpus_jsonl",
    "load_golden_jsonl",
    "load_markdown_file",
    "load_path",
    "load_pipeline_config",
    "load_text_file",
    "mmr_rerank",
    "mrr",
    "multi_query",
    "normalize_scores",
    "pack_context",
    "reciprocal_rank_fusion",
    "rerank",
    "rewrite_query",
    "run_pipeline",
    "save_corpus_jsonl",
    "score_answer",
    "should_answer",
    "truncate_to_tokens",
]
