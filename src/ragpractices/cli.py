"""Command-line entry point: ``ragpractices``."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from ragpractices import __version__
from ragpractices.checklist import get_checklist
from ragpractices.chunking import chunk_by_headings, chunk_text
from ragpractices.citations import attach_citations
from ragpractices.groundedness import check_groundedness
from ragpractices.hybrid import hybrid_search
from ragpractices.ingest import corpus_to_hybrid_docs, load_path, save_corpus_jsonl
from ragpractices.packing import pack_context
from ragpractices.rerank import mmr_rerank, rerank
from ragpractices.rewrite import multi_query, rewrite_query
from ragpractices.rubric import DIMENSIONS, format_scorecard, score_answer


def _parse_scores(spec: str) -> dict[str, int]:
    """Parse ``groundedness=2,relevance=1,...`` into a score dict."""
    scores: dict[str, int] = {}
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"expected name=value, got {part!r}")
        name, raw = part.split("=", 1)
        name = name.strip()
        try:
            scores[name] = int(raw.strip())
        except ValueError as exc:
            raise ValueError(f"invalid score for {name!r}: {raw!r}") from exc
    return scores


def _prompt_scores() -> dict[str, int]:
    print("Enter scores 0/1/2 for each dimension:", file=sys.stderr)
    scores: dict[str, int] = {}
    for dim in DIMENSIONS:
        while True:
            raw = input(f"  {dim}: ").strip()
            try:
                value = int(raw)
            except ValueError:
                print("    please enter an integer 0, 1, or 2", file=sys.stderr)
                continue
            if value not in (0, 1, 2):
                print("    please enter 0, 1, or 2", file=sys.stderr)
                continue
            scores[dim] = value
            break
    return scores


def _load_hybrid_docs(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    parts = [p.strip() for p in text.split("\n---\n")]
    return [p for p in parts if p]


def _load_answer(spec: str) -> str:
    """Load answer text from a path if it exists, else treat as literal string."""
    path = Path(spec)
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return spec


def _load_cite_sources(path: Path) -> list[dict[str, Any]]:
    """Load sources from JSONL (id+text), JSON list, or hybrid-docs (--- separated)."""
    raw = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix == ".jsonl":
        sources: list[dict[str, Any]] = []
        for i, line in enumerate(raw.splitlines()):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"JSONL line {i + 1} must be an object")
            if "id" not in obj:
                obj = {**obj, "id": f"doc-{i}"}
            if "text" not in obj and "document" not in obj and "snippet" not in obj:
                raise ValueError(
                    f"JSONL line {i + 1} needs text/document/snippet field"
                )
            sources.append(obj)
        return sources

    if suffix == ".json":
        data = json.loads(raw)
        if isinstance(data, list):
            out: list[dict[str, Any]] = []
            for i, item in enumerate(data):
                if isinstance(item, str):
                    out.append({"id": f"doc-{i}", "text": item})
                elif isinstance(item, dict):
                    if "id" not in item:
                        item = {**item, "id": f"doc-{i}"}
                    out.append(item)
                else:
                    raise ValueError(f"JSON list item {i} must be str or object")
            return out
        if isinstance(data, dict) and "sources" in data:
            return _normalize_sources_list(data["sources"])
        raise ValueError("JSON sources must be a list or {\"sources\": [...]}")

    # Hybrid-docs style: documents separated by \n---\n with generated ids
    docs = _load_hybrid_docs(path)
    return [{"id": f"doc-{i}", "text": d} for i, d in enumerate(docs)]


def _normalize_sources_list(items: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, item in enumerate(items):
        if isinstance(item, str):
            out.append({"id": f"doc-{i}", "text": item})
        elif isinstance(item, dict):
            row = dict(item)
            if "id" not in row:
                row["id"] = f"doc-{i}"
            out.append(row)
        else:
            raise ValueError(f"source item {i} must be str or object")
    return out


def cmd_chunk(args: argparse.Namespace) -> int:
    path = Path(args.path)
    text = path.read_text(encoding="utf-8")
    if args.by_headings:
        chunks = chunk_by_headings(text, max_chars=args.max_chars)
    else:
        pieces = chunk_text(text, chunk_size=args.chunk_size, overlap=args.overlap)
        chunks = [{"text": p, "heading": ""} for p in pieces]
    json.dump(chunks, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    if args.scores:
        scores = _parse_scores(args.scores)
    else:
        scores = _prompt_scores()
    result = score_answer(scores)
    sys.stdout.write(format_scorecard(result))
    return 0 if result["passed"] else 1


def cmd_checklist(_args: argparse.Namespace) -> int:
    sys.stdout.write(get_checklist())
    if not get_checklist().endswith("\n"):
        sys.stdout.write("\n")
    return 0


def cmd_hybrid(args: argparse.Namespace) -> int:
    docs_path = Path(args.docs)
    documents = _load_hybrid_docs(docs_path)
    dense_scores: list[float] | None = None
    if args.dense:
        dense_raw = json.loads(Path(args.dense).read_text(encoding="utf-8"))
        if not isinstance(dense_raw, list):
            raise ValueError("--dense must be a JSON list of floats")
        dense_scores = [float(x) for x in dense_raw]

    results = hybrid_search(
        args.query,
        documents,
        dense_scores,
        rrf_k=args.rrf_k,
        alpha=args.alpha,
        fusion=args.fusion,
    )
    top = max(0, args.top)
    if top:
        results = results[:top]
    json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    docs = load_path(args.path, glob=args.glob)
    summary = [
        {"id": d.id, "path": d.path, "chars": len(d.text)} for d in docs
    ]

    if args.out:
        save_corpus_jsonl(docs, args.out)
        print(f"ingested {len(docs)} document(s) -> {args.out}")
        for row in summary:
            print(f"  {row['id']}\t{row['chars']} chars\t{row['path']}")
        return 0

    if args.stdout:
        for doc in docs:
            sys.stdout.write(json.dumps(asdict(doc), ensure_ascii=False))
            sys.stdout.write("\n")
        return 0

    # Default: short human summary table (not full text).
    print(f"ingested {len(docs)} document(s)")
    if not docs:
        return 0
    id_w = max(len("id"), max(len(r["id"]) for r in summary))
    chars_w = max(len("chars"), max(len(str(r["chars"])) for r in summary))
    header = f"{'id':<{id_w}}  {'chars':>{chars_w}}  path"
    print(header)
    print("-" * len(header))
    for row in summary:
        print(f"{row['id']:<{id_w}}  {row['chars']:>{chars_w}}  {row['path']}")
    return 0


def cmd_rewrite(args: argparse.Namespace) -> int:
    if args.multi:
        variants = multi_query(args.query)
        json.dump({"query": args.query, "variants": variants}, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    result = rewrite_query(args.query, mode=args.mode)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_rerank(args: argparse.Namespace) -> int:
    documents = _load_hybrid_docs(Path(args.docs))
    top_k = args.top if args.top is not None else None
    if args.mmr:
        k = top_k if top_k is not None else 5
        results = mmr_rerank(
            args.query,
            documents,
            lambda_mult=args.lambda_mult,
            top_k=k,
        )
    else:
        results = rerank(args.query, documents, top_k=top_k)
    json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_cite(args: argparse.Namespace) -> int:
    answer = _load_answer(args.answer)
    sources = _load_cite_sources(Path(args.sources))
    result = attach_citations(answer, sources, style=args.style)
    if args.json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(result["full_text"])
        if not result["full_text"].endswith("\n"):
            sys.stdout.write("\n")
    return 0



def cmd_pack(args: argparse.Namespace) -> int:
    docs_path = Path(args.docs)
    # Prefer cite-sources loader (jsonl / json / ---) then pack text fields
    sources = _load_cite_sources(docs_path)
    docs: list[dict[str, Any]] = []
    for s in sources:
        text = str(s.get("text") or s.get("document") or s.get("snippet") or "")
        row: dict[str, Any] = {"id": s.get("id"), "text": text}
        if "score" in s:
            row["score"] = s["score"]
        docs.append(row)

    result = pack_context(
        docs,
        max_tokens=args.max_tokens,
        separator=args.separator,
        preserve_order=not args.by_score,
        truncate=args.truncate,
    )
    sys.stdout.write(result.packed_text)
    if result.packed_text and not result.packed_text.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()
    summary = {
        "included": result.included,
        "omitted": result.omitted,
        "estimated_tokens": result.estimated_tokens,
        "max_tokens": result.max_tokens,
    }
    print("---", file=sys.stderr)
    json.dump(summary, sys.stderr, ensure_ascii=False, indent=2)
    sys.stderr.write("\n")
    sys.stderr.flush()
    return 0


def cmd_ground(args: argparse.Namespace) -> int:
    answer = _load_answer(args.answer)
    sources = _load_cite_sources(Path(args.sources))
    report = check_groundedness(
        answer,
        sources,
        min_overlap=args.min_overlap,
    )
    payload = {
        "score": report.score,
        "supported_word_ratio": report.supported_word_ratio,
        "unsupported_sentences": report.unsupported_sentences,
        "per_source": report.per_source,
        "notes": report.notes,
    }
    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"score: {report.score:.4f}")
        print(f"supported_word_ratio: {report.supported_word_ratio:.4f}")
        if report.unsupported_sentences:
            print("unsupported_sentences:")
            for s in report.unsupported_sentences:
                print(f"  - {s}")
        else:
            print("unsupported_sentences: (none)")
        print(f"notes: {report.notes}")
    return 0 if report.score >= args.min_overlap else 1


def _default_demo_docs() -> Path:
    """Prefer examples/hybrid-docs.txt, else examples/ingest-sample."""
    root = Path.cwd()
    hybrid = root / "examples" / "hybrid-docs.txt"
    if hybrid.is_file():
        return hybrid
    sample = root / "examples" / "ingest-sample"
    if sample.is_dir():
        return sample
    return hybrid


def run_demo_pipeline(
    query: str,
    docs_path: Path,
    *,
    max_tokens: int = 200,
    rewrite: bool = True,
) -> int:
    """Shared end-to-end demo used by CLI and examples/e2e_demo.py."""
    print("=== ragpractices demo ===")
    print(f"query: {query}")
    print(f"docs:  {docs_path}")
    print()

    # 1. Load
    print("1) Load documents")
    if docs_path.is_dir():
        corpus = load_path(docs_path)
        documents = corpus_to_hybrid_docs(corpus)
        ids = [d.id for d in corpus]
        print(f"   loaded {len(documents)} file(s) via ingest")
    else:
        documents = _load_hybrid_docs(docs_path)
        ids = [f"doc-{i}" for i in range(len(documents))]
        print(f"   loaded {len(documents)} section(s) from file")
    print()

    # 2. Optional rewrite
    search_query = query
    if rewrite:
        print("2) Rewrite query (expand)")
        rw = rewrite_query(query, mode="expand")
        search_query = rw["rewritten"]
        print(f"   original:  {rw['original']}")
        print(f"   rewritten: {search_query}")
        print()
    else:
        print("2) Rewrite skipped")
        print()

    # 3. Hybrid search
    print("3) Hybrid search (keyword / RRF)")
    hits = hybrid_search(search_query, documents, fusion="rrf")
    top_hits = hits[: min(5, len(hits))]
    for h in top_hits:
        snippet = h["document"].replace("\n", " ")[:80]
        print(f"   [{h['index']}] score={h['score']:.4f}  {snippet}")
    print()

    # 4. Rerank
    print("4) Rerank (keyword blend)")
    cand_docs = [h["document"] for h in top_hits]
    cand_ids = [ids[h["index"]] for h in top_hits]
    ranked = rerank(search_query, cand_docs, top_k=min(3, len(cand_docs)))
    for r in ranked:
        print(f"   [{cand_ids[r['index']]}] score={r['score']:.4f}")
    print()

    # 5. Pack context
    print(f"5) Pack context (max_tokens={max_tokens})")
    pack_docs = [
        {
            "id": cand_ids[r["index"]],
            "text": r["document"],
            "score": r["score"],
        }
        for r in ranked
    ]
    packed = pack_context(pack_docs, max_tokens=max_tokens, preserve_order=True)
    print(f"   included: {packed.included}")
    print(f"   omitted:  {packed.omitted}")
    print(f"   estimated_tokens: {packed.estimated_tokens}/{packed.max_tokens}")
    preview = packed.packed_text.replace("\n", " ")[:120]
    print(f"   preview: {preview}...")
    print()

    # 6. Cite a canned answer
    print("6) Attach citations (canned answer)")
    canned = (
        "Refunds are accepted within 30 days of purchase. "
        "Standard shipping takes 5-7 business days."
    )
    cite_sources = [
        {"id": d["id"], "text": d["text"], "score": d.get("score")}
        for d in pack_docs
    ]
    cited = attach_citations(canned, cite_sources, style="numeric")
    print(cited["full_text"][:400])
    if len(cited["full_text"]) > 400:
        print("   …")
    print()

    # 7. Groundedness
    print("7) Groundedness check (heuristic stub)")
    report = check_groundedness(canned, cite_sources)
    print(f"   score: {report.score:.4f}")
    if report.unsupported_sentences:
        print("   unsupported:")
        for s in report.unsupported_sentences:
            print(f"     - {s}")
    else:
        print("   unsupported_sentences: (none)")
    print(f"   notes: {report.notes}")
    print()
    print("=== demo complete ===")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    docs_path = Path(args.docs) if args.docs else _default_demo_docs()
    if not docs_path.exists():
        raise ValueError(
            f"docs path not found: {docs_path} "
            "(run from repo root or pass --docs)"
        )
    return run_demo_pipeline(
        args.query,
        docs_path,
        max_tokens=args.max_tokens,
        rewrite=not args.no_rewrite,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ragpractices",
        description=(
            "Toolkit helpers for RAG chunking, ingest, hybrid search, "
            "rewrite, rerank, packing, groundedness, citations, "
            "scoring, and checklists."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_chunk = sub.add_parser("chunk", help="Chunk a text or Markdown file to JSON")
    p_chunk.add_argument("path", help="Path to a UTF-8 text/Markdown file")
    p_chunk.add_argument(
        "--chunk-size",
        type=int,
        default=800,
        help="Max characters per window (default: 800)",
    )
    p_chunk.add_argument(
        "--overlap",
        type=int,
        default=100,
        help="Overlap between windows (default: 100)",
    )
    p_chunk.add_argument(
        "--by-headings",
        action="store_true",
        help="Split on Markdown ATX headings first",
    )
    p_chunk.add_argument(
        "--max-chars",
        type=int,
        default=1200,
        help="Max chars per heading section chunk (default: 1200)",
    )
    p_chunk.set_defaults(func=cmd_chunk)

    p_score = sub.add_parser(
        "score",
        help="Score an answer with the groundedness/relevance rubric",
    )
    p_score.add_argument(
        "--scores",
        metavar="SPEC",
        help=(
            "Comma-separated scores, e.g. "
            "groundedness=2,relevance=1,completeness=2,citation_quality=1"
        ),
    )
    p_score.set_defaults(func=cmd_score)

    p_check = sub.add_parser(
        "checklist",
        help="Print a short RAG principles checklist",
    )
    p_check.set_defaults(func=cmd_checklist)

    p_hybrid = sub.add_parser(
        "hybrid",
        help="Hybrid (keyword + optional dense) search over a docs file",
    )
    p_hybrid.add_argument("query", help="Search query string")
    p_hybrid.add_argument(
        "--docs",
        required=True,
        help="Path to a UTF-8 text file with documents separated by \\n---\\n",
    )
    p_hybrid.add_argument(
        "--dense",
        help="Optional path to a JSON list of floats (same length as documents)",
    )
    p_hybrid.add_argument(
        "--fusion",
        choices=("rrf", "weighted"),
        default="rrf",
        help="Fusion mode (default: rrf)",
    )
    p_hybrid.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="Dense weight for weighted fusion in [0, 1] (default: 0.5)",
    )
    p_hybrid.add_argument(
        "--rrf-k",
        type=int,
        default=60,
        help="RRF smoothing k (default: 60)",
    )
    p_hybrid.add_argument(
        "--top",
        type=int,
        default=0,
        metavar="K",
        help="Return only the top K results (default: all)",
    )
    p_hybrid.set_defaults(func=cmd_hybrid)

    p_ingest = sub.add_parser(
        "ingest",
        help="Load text/Markdown files into a corpus (summary or JSONL)",
    )
    p_ingest.add_argument(
        "path",
        help="File or directory to ingest (UTF-8 .txt / .md by default)",
    )
    p_ingest.add_argument(
        "--out",
        metavar="FILE",
        help="Write full corpus as JSONL to FILE",
    )
    p_ingest.add_argument(
        "--glob",
        metavar="PATTERN",
        help="Glob under a directory (default: **/*.txt and **/*.md)",
    )
    p_ingest.add_argument(
        "--stdout",
        action="store_true",
        help="Write full corpus JSONL to stdout (instead of a summary table)",
    )
    p_ingest.set_defaults(func=cmd_ingest)

    p_rewrite = sub.add_parser(
        "rewrite",
        help="Deterministic query rewrite / multi-query variants (no LLM)",
    )
    p_rewrite.add_argument("query", help="Query string to rewrite")
    p_rewrite.add_argument(
        "--mode",
        choices=("expand", "clarify", "hyphenate_split"),
        default="expand",
        help="Rewrite mode (default: expand)",
    )
    p_rewrite.add_argument(
        "--multi",
        action="store_true",
        help="Emit 2–3 multi-query variants instead of a single rewrite",
    )
    p_rewrite.set_defaults(func=cmd_rewrite)

    p_rerank = sub.add_parser(
        "rerank",
        help="Rerank documents by keyword overlap or MMR",
    )
    p_rerank.add_argument("query", help="Query string")
    p_rerank.add_argument(
        "--docs",
        required=True,
        help="Path to a UTF-8 text file with documents separated by \\n---\\n",
    )
    p_rerank.add_argument(
        "--mmr",
        action="store_true",
        help="Use Maximal Marginal Relevance instead of keyword blend",
    )
    p_rerank.add_argument(
        "--top",
        type=int,
        default=None,
        metavar="K",
        help="Return only the top K results (MMR default: 5)",
    )
    p_rerank.add_argument(
        "--lambda-mult",
        type=float,
        default=0.7,
        dest="lambda_mult",
        help="MMR lambda in [0, 1] (default: 0.7)",
    )
    p_rerank.set_defaults(func=cmd_rerank)

    p_cite = sub.add_parser(
        "cite",
        help="Attach inline citations and a Sources appendix to an answer",
    )
    p_cite.add_argument(
        "--answer",
        required=True,
        help="Answer text, or path to a UTF-8 file containing the answer",
    )
    p_cite.add_argument(
        "--sources",
        required=True,
        help=(
            "Path to sources: JSONL (id+text), JSON list, or hybrid-docs "
            "file (--- separated, ids generated)"
        ),
    )
    p_cite.add_argument(
        "--style",
        choices=("numeric", "bracketed"),
        default="numeric",
        help="Citation style (default: numeric)",
    )
    p_cite.add_argument(
        "--json",
        action="store_true",
        help="Emit answer/sources_block/full_text as JSON",
    )
    p_cite.set_defaults(func=cmd_cite)


    p_pack = sub.add_parser(
        "pack",
        help="Pack documents under a token budget (~4 chars/token heuristic)",
    )
    p_pack.add_argument(
        "--docs",
        required=True,
        help=(
            "Path to docs: JSONL (id+text), JSON list, or hybrid-docs "
            "file (--- separated)"
        ),
    )
    p_pack.add_argument(
        "--max-tokens",
        type=int,
        default=500,
        help="Token budget (default: 500; ~4 chars/token)",
    )
    p_pack.add_argument(
        "--separator",
        default="\n\n---\n\n",
        help="Separator between packed docs",
    )
    p_pack.add_argument(
        "--by-score",
        action="store_true",
        help="Sort by score descending before packing (default: preserve order)",
    )
    p_pack.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate the last partial doc to fill remaining budget",
    )
    p_pack.set_defaults(func=cmd_pack)

    p_ground = sub.add_parser(
        "ground",
        help="Heuristic groundedness check (word overlap stub, not NLI)",
    )
    p_ground.add_argument(
        "--answer",
        required=True,
        help="Answer text, or path to a UTF-8 file containing the answer",
    )
    p_ground.add_argument(
        "--sources",
        required=True,
        help=(
            "Path to sources: JSONL (id+text), JSON list, or hybrid-docs "
            "file (--- separated)"
        ),
    )
    p_ground.add_argument(
        "--min-overlap",
        type=float,
        default=0.0,
        help="Soft gate: exit 1 if score is below this (default: 0.0)",
    )
    p_ground.add_argument(
        "--json",
        action="store_true",
        help="Emit full GroundednessReport fields as JSON",
    )
    p_ground.set_defaults(func=cmd_ground)

    p_demo = sub.add_parser(
        "demo",
        help="End-to-end demo: rewrite → hybrid → rerank → pack → cite → ground",
    )
    p_demo.add_argument(
        "--query",
        default="refund shipping policy",
        help="Query string (default: refund shipping policy)",
    )
    p_demo.add_argument(
        "--docs",
        default=None,
        help=(
            "Docs path (file or directory). Default: examples/hybrid-docs.txt "
            "or examples/ingest-sample when run from repo root"
        ),
    )
    p_demo.add_argument(
        "--max-tokens",
        type=int,
        default=200,
        help="Packing budget (default: 200)",
    )
    p_demo.add_argument(
        "--no-rewrite",
        action="store_true",
        help="Skip the query-rewrite step",
    )
    p_demo.set_defaults(func=cmd_demo)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
