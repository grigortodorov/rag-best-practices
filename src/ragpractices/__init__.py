"""ragpractices — small helpers for RAG chunking, rubrics, checklists, hybrid search, ingest, and eval harnesses."""

from ragpractices.canaries import (
    Canary,
    CanaryReport,
    load_canaries_jsonl,
    run_canaries,
)
from ragpractices.chunk_ab import (
    ChunkAbReport,
    compare_chunkers,
    format_chunk_ab_table,
)
from ragpractices.cite_spans import (
    CiteSpanReport,
    verify_citation_spans,
)
from ragpractices.claim_check import (
    ClaimCheckReport,
    ClaimResult,
    EntityHit,
    check_claims,
    extract_sensitive_tokens,
    split_claims,
)
from ragpractices.position_stress import (
    PositionStressReport,
    run_position_stress,
)
from ragpractices.abstain import AbstainResult, Decision, should_answer
from ragpractices.checklist import get_checklist
from ragpractices.chunking import chunk_by_headings, chunk_text
from ragpractices.citations import (
    Citation,
    attach_citations,
    build_sources_block,
    format_inline_citations,
)
from ragpractices.compare import (
    CompareReport,
    StrategyResult,
    compare_strategies,
    format_compare_table,
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
from ragpractices.filters import filter_docs, load_docs_jsonl
from ragpractices.groundedness import GroundednessReport, check_groundedness
from ragpractices.html_ingest import html_to_text, load_html_file
from ragpractices.hybrid import (
    hybrid_search,
    keyword_score,
    normalize_scores,
    reciprocal_rank_fusion,
)
from ragpractices.ingest import (
    Document,
    content_hash,
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
from ragpractices.prompts import build_clarify_prompt, build_grounded_prompt
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

__version__ = "0.9.0"

__all__ = [
    "DIMENSIONS",
    "Canary",
    "CanaryReport",
    "ChunkAbReport",
    "CiteSpanReport",
    "ClaimCheckReport",
    "ClaimResult",
    "EntityHit",
    "PositionStressReport",
    "AbstainResult",
    "CaseResult",
    "ChunkIssue",
    "ChunkStats",
    "Citation",
    "CompareReport",
    "Decision",
    "DedupeResult",
    "Document",
    "EvalReport",
    "GoldenCase",
    "GroundednessReport",
    "PackResult",
    "PipelineResult",
    "StageTrace",
    "StrategyResult",
    "__version__",
    "attach_citations",
    "build_clarify_prompt",
    "build_grounded_prompt",
    "build_sources_block",
    "check_claims",
    "check_groundedness",
    "chunk_by_headings",
    "chunk_stats",
    "chunk_text",
    "compare_chunkers",
    "compare_strategies",
    "content_hash",
    "corpus_to_hybrid_docs",
    "dedupe_near",
    "estimate_tokens",
    "evaluate_retrieval",
    "extract_sensitive_tokens",
    "filter_docs",
    "flag_chunks",
    "format_chunk_ab_table",
    "format_compare_table",
    "format_inline_citations",
    "format_scorecard",
    "get_checklist",
    "hit_at_k",
    "html_to_text",
    "hybrid_search",
    "keyword_score",
    "load_canaries_jsonl",
    "load_corpus_jsonl",
    "load_docs_jsonl",
    "load_golden_jsonl",
    "load_html_file",
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
    "run_canaries",
    "run_pipeline",
    "run_position_stress",
    "save_corpus_jsonl",
    "score_answer",
    "should_answer",
    "split_claims",
    "truncate_to_tokens",
    "verify_citation_spans",
]
