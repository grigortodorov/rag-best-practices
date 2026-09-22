"""Chunking A/B evaluation: document-level recall after chunking (stdlib only).

Educational harness for comparing chunk strategies on the same corpus and
golden queries. Each strategy wraps existing chunkers (:func:`chunk_text`,
:func:`chunk_by_headings`) and assigns stable chunk ids ``{doc_id}:{i}``.

**Document-level hit semantics:** golden ``expected`` / ``expected_ids`` are
**source document ids**, not chunk ids. After retrieval over chunks, a case
hits if any retrieved chunk's parent document id is in the expected set.
This isolates "did the right source land in top-k after this chunking?" from
exact chunk-boundary labels.

Not a production A/B platform—use it to catch chunking regressions locally.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from ragpractices.chunking import chunk_by_headings, chunk_text
from ragpractices.eval import GoldenCase, hit_at_k, load_golden_jsonl, mrr
from ragpractices.hybrid import hybrid_search, keyword_score
from ragpractices.ingest import Document, load_path

STRATEGY_NAMES = (
    "fixed",
    "fixed_small",
    "fixed_large",
    "headings",
)


@dataclass
class ChunkRecord:
    """One chunk produced by a strategy."""

    chunk_id: str
    doc_id: str
    text: str
    index: int


@dataclass
class ChunkStrategyResult:
    """Aggregate document-level metrics for one chunking strategy."""

    name: str
    hit_at_k_rate: float
    mean_mrr: float
    n_cases: int
    n_chunks: int
    k: int


@dataclass
class ChunkAbReport:
    """Side-by-side chunking strategy comparison."""

    k: int
    n_cases: int
    n_sources: int
    strategies: list[ChunkStrategyResult] = field(default_factory=list)
    ranking: list[str] = field(default_factory=list)
    notes: str = (
        "Educational chunking A/B (document-level hit@k + MRR after chunking). "
        "Golden expected_ids are source doc ids; a hit counts if any retrieved "
        "chunk's parent doc is expected. Ranking: higher hit@k, then higher MRR."
    )


def _normalize_sources(
    sources: Sequence[str | dict[str, Any] | Document],
) -> list[dict[str, str]]:
    """Normalize to ``[{"id", "text"}, ...]``."""
    out: list[dict[str, str]] = []
    for i, item in enumerate(sources):
        if isinstance(item, Document):
            out.append({"id": str(item.id), "text": item.text})
        elif isinstance(item, str):
            out.append({"id": f"doc-{i}", "text": item})
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("document") or "")
            sid = str(item.get("id", f"doc-{i}"))
            out.append({"id": sid, "text": text})
        else:
            raise TypeError(f"source {i} must be str, dict, or Document")
    return out


def _chunk_fixed(text: str, *, size: int, overlap: int) -> list[str]:
    return chunk_text(text, chunk_size=size, overlap=overlap)


def _chunk_headings(text: str, *, max_chars: int = 600) -> list[str]:
    parts = chunk_by_headings(text, max_chars=max_chars)
    return [str(p["text"]) for p in parts if str(p.get("text") or "").strip()]


def apply_strategy(name: str, sources: Sequence[dict[str, str]]) -> list[ChunkRecord]:
    """Chunk all sources with ``name``; return :class:`ChunkRecord` list."""
    if name not in STRATEGY_NAMES:
        raise ValueError(
            f"unknown strategy {name!r}; known: {', '.join(STRATEGY_NAMES)}"
        )
    records: list[ChunkRecord] = []
    for src in sources:
        doc_id = src["id"]
        text = src["text"]
        if name == "fixed":
            pieces = _chunk_fixed(text, size=400, overlap=50)
        elif name == "fixed_small":
            pieces = _chunk_fixed(text, size=120, overlap=20)
        elif name == "fixed_large":
            pieces = _chunk_fixed(text, size=800, overlap=100)
        else:  # headings
            pieces = _chunk_headings(text, max_chars=600)
        if not pieces and text.strip():
            pieces = [text]
        for i, piece in enumerate(pieces):
            records.append(
                ChunkRecord(
                    chunk_id=f"{doc_id}:{i}",
                    doc_id=doc_id,
                    text=piece,
                    index=i,
                )
            )
    return records


def _parent_doc_ids(chunk_ids: Sequence[str], chunk_to_doc: dict[str, str]) -> list[str]:
    """Map ranked chunk ids to parent doc ids (preserving order, unique)."""
    seen: set[str] = set()
    parents: list[str] = []
    for cid in chunk_ids:
        doc_id = chunk_to_doc.get(cid, cid.rsplit(":", 1)[0] if ":" in cid else cid)
        if doc_id not in seen:
            seen.add(doc_id)
            parents.append(doc_id)
    return parents


def _retrieve_chunk_ids(
    query: str,
    chunks: list[ChunkRecord],
    *,
    mode: str = "hybrid",
) -> list[str]:
    texts = [c.text for c in chunks]
    ids = [c.chunk_id for c in chunks]
    if not texts:
        return []
    if mode == "keyword":
        scores = keyword_score(query, texts)
        order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
        return [ids[i] for i in order]
    hits = hybrid_search(query, texts, fusion="rrf")
    return [ids[h["index"]] for h in hits]


def compare_chunkers(
    sources: Sequence[str | dict[str, Any] | Document],
    cases: Sequence[GoldenCase],
    *,
    k: int = 5,
    strategies: Sequence[str] | None = None,
    retrieve_mode: str = "hybrid",
) -> ChunkAbReport:
    """Compare chunk strategies via document-level hit@k / MRR.

    Args:
        sources: Source documents (strings, dicts with ``id``/``text``, or
            :class:`Document`).
        cases: Golden cases whose ``expected_ids`` are **source doc ids**.
        k: Cutoff for hit@k over parent docs derived from retrieved chunks.
        strategies: Subset of strategy names; default all four.
        retrieve_mode: ``"hybrid"`` (default) or ``"keyword"`` over chunks.

    Returns:
        :class:`ChunkAbReport` with per-strategy rates and a ranking.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    if retrieve_mode not in ("hybrid", "keyword"):
        raise ValueError("retrieve_mode must be 'hybrid' or 'keyword'")

    norm = _normalize_sources(sources)
    names = list(strategies) if strategies is not None else list(STRATEGY_NAMES)
    for name in names:
        if name not in STRATEGY_NAMES:
            raise ValueError(
                f"unknown strategy {name!r}; known: {', '.join(STRATEGY_NAMES)}"
            )

    results: list[ChunkStrategyResult] = []
    for name in names:
        chunks = apply_strategy(name, norm)
        chunk_to_doc = {c.chunk_id: c.doc_id for c in chunks}
        hits = 0
        mrr_sum = 0.0
        for case in cases:
            ranked_chunks = _retrieve_chunk_ids(
                case.query, chunks, mode=retrieve_mode
            )
            parent_ids = _parent_doc_ids(ranked_chunks, chunk_to_doc)
            h = hit_at_k(parent_ids, case.expected_ids, k)
            r = mrr(parent_ids, case.expected_ids)
            if h:
                hits += 1
            mrr_sum += r
        n = len(cases)
        results.append(
            ChunkStrategyResult(
                name=name,
                hit_at_k_rate=(hits / n) if n else 0.0,
                mean_mrr=(mrr_sum / n) if n else 0.0,
                n_cases=n,
                n_chunks=len(chunks),
                k=k,
            )
        )

    ranking = sorted(
        results,
        key=lambda s: (-s.hit_at_k_rate, -s.mean_mrr, s.name),
    )
    return ChunkAbReport(
        k=k,
        n_cases=len(cases),
        n_sources=len(norm),
        strategies=results,
        ranking=[s.name for s in ranking],
    )


def load_sources(path: str | Path) -> list[dict[str, str]]:
    """Load sources from a directory, hybrid-docs file, or corpus JSONL."""
    p = Path(path)
    if p.is_dir():
        corpus = load_path(p)
        return [{"id": d.id, "text": d.text} for d in corpus]
    suffix = p.suffix.lower()
    raw = p.read_text(encoding="utf-8")
    if suffix == ".jsonl":
        out: list[dict[str, str]] = []
        for i, line in enumerate(raw.splitlines()):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"JSONL line {i + 1} must be an object")
            text = str(obj.get("text") or obj.get("document") or "")
            sid = str(obj.get("id", f"doc-{i}"))
            out.append({"id": sid, "text": text})
        return out
    parts = [x.strip() for x in raw.split("\n---\n") if x.strip()]
    return [{"id": f"doc-{i}", "text": t} for i, t in enumerate(parts)]


def format_chunk_ab_table(report: ChunkAbReport) -> str:
    """Plain-text table of chunking strategy metrics plus ranking."""
    rows = report.strategies
    if not rows:
        return "n_cases: 0\n(no strategies)\n"
    name_w = max(len("strategy"), max(len(s.name) for s in rows))
    hit_label = f"hit@{report.k}"
    lines = [
        f"n_sources: {report.n_sources}  n_cases: {report.n_cases}  k: {report.k}",
        f"{'strategy':<{name_w}}  {hit_label:>8}  {'mean_mrr':>8}  {'chunks':>6}",
        f"{'-' * name_w}  {'-' * 8}  {'-' * 8}  {'-' * 6}",
    ]
    for s in rows:
        lines.append(
            f"{s.name:<{name_w}}  {s.hit_at_k_rate:8.4f}  {s.mean_mrr:8.4f}  {s.n_chunks:6d}"
        )
    lines.append("")
    lines.append(f"ranking: {' > '.join(report.ranking)}")
    lines.append(f"notes: {report.notes}")
    return "\n".join(lines) + "\n"


def report_to_dict(report: ChunkAbReport) -> dict[str, Any]:
    """Serialize a :class:`ChunkAbReport` to a JSON-friendly dict."""
    return {
        "k": report.k,
        "n_cases": report.n_cases,
        "n_sources": report.n_sources,
        "ranking": list(report.ranking),
        "notes": report.notes,
        "strategies": [
            {
                "name": s.name,
                "hit_at_k_rate": s.hit_at_k_rate,
                "mean_mrr": s.mean_mrr,
                "n_cases": s.n_cases,
                "n_chunks": s.n_chunks,
                "k": s.k,
            }
            for s in report.strategies
        ],
    }


__all__ = [
    "STRATEGY_NAMES",
    "ChunkAbReport",
    "ChunkRecord",
    "ChunkStrategyResult",
    "apply_strategy",
    "compare_chunkers",
    "format_chunk_ab_table",
    "load_golden_jsonl",
    "load_sources",
    "report_to_dict",
]
