"""Command-line entry point: ``ragpractices``."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from ragpractices import __version__
from ragpractices.abstain import should_answer
from ragpractices.canaries import (
    format_canary_report,
    load_canaries_jsonl,
    report_to_dict as canary_report_to_dict,
    run_canaries,
)
from ragpractices.checklist import get_checklist
from ragpractices.chunk_ab import (
    compare_chunkers,
    format_chunk_ab_table,
    load_sources as load_chunk_ab_sources,
    report_to_dict as chunk_ab_report_to_dict,
)
from ragpractices.chunking import chunk_by_headings, chunk_text
from ragpractices.citations import attach_citations
from ragpractices.cite_spans import (
    format_cite_span_report,
    report_to_dict as cite_span_report_to_dict,
    verify_citation_spans,
)
from ragpractices.claim_check import (
    check_claims,
    format_claim_check_report,
    report_to_dict as claim_check_report_to_dict,
)
from ragpractices.conflict_check import (
    check_conflicts,
    format_conflict_report,
    report_to_dict as conflict_report_to_dict,
)
from ragpractices.compare import compare_strategies, format_compare_table, report_to_dict as compare_report_to_dict
from ragpractices.eval import evaluate_retrieval, load_golden_jsonl, report_to_dict
from ragpractices.filters import filter_docs, load_docs_jsonl
from ragpractices.position_stress import (
    format_position_stress_report,
    report_to_dict as position_stress_report_to_dict,
    run_position_stress,
)
from ragpractices.groundedness import check_groundedness
from ragpractices.html_ingest import html_to_text, load_html_file
from ragpractices.hybrid import hybrid_search
from ragpractices.ingest import (
    content_hash,
    corpus_to_hybrid_docs,
    load_corpus_jsonl,
    load_path,
    save_corpus_jsonl,
)
from ragpractices.packing import pack_context
from ragpractices.pipeline import load_pipeline_config, result_to_dict, run_pipeline
from ragpractices.prompts import build_clarify_prompt, build_grounded_prompt
from ragpractices.quality import chunk_stats, dedupe_near, flag_chunks, stats_to_dict
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



def _load_docs_with_ids(path: Path) -> tuple[list[str], list[str]]:
    """Load documents and stable ids from hybrid-docs, corpus JSONL, or a directory."""
    if path.is_dir():
        corpus = load_path(path)
        return corpus_to_hybrid_docs(corpus), [d.id for d in corpus]

    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        # Prefer corpus schema; fall back to cite-sources (id+text)
        try:
            corpus = load_corpus_jsonl(path)
            if corpus:
                return [d.text for d in corpus], [d.id for d in corpus]
        except (OSError, ValueError, json.JSONDecodeError, TypeError, KeyError):
            pass
        sources = _load_cite_sources(path)
        texts = [
            str(s.get("text") or s.get("document") or s.get("snippet") or "")
            for s in sources
        ]
        ids = [str(s.get("id", f"doc-{i}")) for i, s in enumerate(sources)]
        return texts, ids

    documents = _load_hybrid_docs(path)
    ids = [f"doc-{i}" for i in range(len(documents))]
    return documents, ids


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

    # 8. Fail-closed decide
    print("8) Fail-closed decide (abstain gate)")
    top_score = ranked[0]["score"] if ranked else None
    empty = len(ranked) == 0
    decision = should_answer(
        top_score=top_score,
        groundedness=report.score,
        empty_retrieval=empty,
    )
    print(f"   decision: {decision.decision}")
    print(f"   reason:   {decision.reason}")
    if decision.decision != "answer":
        print("   skipping confident answer presentation (fail closed)")
    print()
    print("=== demo complete ===")
    return 0



def cmd_eval(args: argparse.Namespace) -> int:
    """Offline retrieval eval against a golden JSONL set."""
    cases = load_golden_jsonl(args.golden)
    docs_path = Path(args.docs)
    documents, ids = _load_docs_with_ids(docs_path)
    k = max(1, int(args.k))

    def retrieve_fn(query: str) -> list[str]:
        hits = hybrid_search(query, documents, fusion="rrf")
        # Full ranking for MRR; hit@k still cuts at k inside evaluate_retrieval.
        return [ids[h["index"]] for h in hits]

    report = evaluate_retrieval(cases, retrieve_fn, k=k)
    payload = report_to_dict(report)
    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"n_cases: {report.n_cases}")
        print(f"hit_at_{k}: {report.hit_at_k_rate:.4f}")
        print(f"mean_mrr: {report.mean_mrr:.4f}")
        print(f"notes: {report.notes}")
        for c in report.cases:
            mark = "HIT" if c.hit_at_k else "MISS"
            print(
                f"  [{c.case_id}] {mark} mrr={c.mrr:.4f} "
                f"expected={c.expected_ids} retrieved={c.retrieved_ids[:k]}"
            )
    failed = False
    if args.min_hit_rate is not None and report.hit_at_k_rate < args.min_hit_rate:
        print(
            f"FAIL: hit_at_{k} {report.hit_at_k_rate:.4f} < min-hit-rate {args.min_hit_rate}",
            file=sys.stderr,
        )
        failed = True
    if args.min_mrr is not None and report.mean_mrr < args.min_mrr:
        print(
            f"FAIL: mean_mrr {report.mean_mrr:.4f} < min-mrr {args.min_mrr}",
            file=sys.stderr,
        )
        failed = True
    return 1 if failed else 0


def cmd_decide(args: argparse.Namespace) -> int:
    result = should_answer(
        top_score=args.top_score,
        groundedness=args.groundedness,
        min_top_score=args.min_top_score,
        min_groundedness=args.min_groundedness,
        empty_retrieval=args.empty_retrieval,
    )
    payload = {"decision": result.decision, "reason": result.reason}
    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"decision: {result.decision}")
        print(f"reason: {result.reason}")
    return 0 if result.decision == "answer" else 1


def cmd_pipeline(args: argparse.Namespace) -> int:
    config = load_pipeline_config(args.config)
    docs_path = Path(args.docs) if args.docs else _default_demo_docs()
    if not docs_path.exists():
        raise ValueError(f"docs path not found: {docs_path}")
    documents, ids = _load_docs_with_ids(docs_path)
    docs = [{"id": i, "text": t} for i, t in zip(ids, documents)]
    result = run_pipeline(config, query=args.query, docs=docs)
    payload = result_to_dict(result)
    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"query: {result.query}")
        print(f"ok: {result.ok}")
        for s in result.stages:
            status = "ok" if s.ok else f"FAIL ({s.error})"
            print(f"  - {s.name}: {s.ms:.2f} ms [{status}] {s.summary}")
        print("final:")
        json.dump(result.final, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    return 0 if result.ok else 1


def cmd_quality(args: argparse.Namespace) -> int:
    documents, ids = _load_docs_with_ids(Path(args.docs))
    stats = chunk_stats(documents, very_short=args.min_chars)
    issues = flag_chunks(
        documents,
        min_chars=args.min_chars,
        max_chars=args.max_chars,
    )
    payload = {
        "stats": stats_to_dict(stats),
        "issues": [
            {"index": i.index, "id": ids[i.index], "kind": i.kind, "detail": i.detail, "length": i.length}
            for i in issues
        ],
    }
    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(
            f"n={stats.n} mean={stats.mean_length:.1f} median={stats.median_length:.1f} "
            f"min={stats.min_length} max={stats.max_length} "
            f"empty={stats.empty_count} very_short={stats.very_short_count}"
        )
        if issues:
            print("issues:")
            for i in issues:
                print(f"  [{ids[i.index]}] {i.kind}: {i.detail}")
        else:
            print("issues: (none)")
    return 0


def cmd_dedupe(args: argparse.Namespace) -> int:
    documents, ids = _load_docs_with_ids(Path(args.docs))
    result = dedupe_near(documents, threshold=args.threshold)
    payload = {
        "threshold": result.threshold,
        "kept_indices": result.kept_indices,
        "kept_ids": [ids[i] for i in result.kept_indices],
        "dropped_pairs": [
            {"kept": a, "dropped": b, "jaccard": sim, "kept_id": ids[a], "dropped_id": ids[b]}
            for a, b, sim in result.dropped_pairs
        ],
    }
    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"kept {len(result.kept_indices)}/{len(documents)} (threshold={result.threshold})")
        print(f"kept_ids: {payload['kept_ids']}")
        if result.dropped_pairs:
            print("dropped:")
            for a, b, sim in result.dropped_pairs:
                print(f"  {ids[b]} ~ {ids[a]} (jaccard={sim:.3f})")
        else:
            print("dropped: (none)")
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


def cmd_compare(args: argparse.Namespace) -> int:
    cases = load_golden_jsonl(args.golden)
    documents, ids = _load_docs_with_ids(Path(args.docs))
    docs = [{"id": i, "text": t} for i, t in zip(ids, documents)]
    k = max(1, int(args.k))
    report = compare_strategies(cases, docs, k=k)
    if args.json:
        json.dump(compare_report_to_dict(report), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_compare_table(report))
    return 0


def cmd_prompt(args: argparse.Namespace) -> int:
    contexts: list[str] = []
    if args.docs:
        documents, _ids = _load_docs_with_ids(Path(args.docs))
        contexts = list(documents)
    if args.clarify:
        hints = [h.strip() for h in (args.missing or "").split(",") if h.strip()]
        text = build_clarify_prompt(args.question, missing_hints=hints or None)
    else:
        text = build_grounded_prompt(
            args.question,
            contexts,
            style=args.style,
            max_context_chars=args.max_context_chars,
        )
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def cmd_filter(args: argparse.Namespace) -> int:
    path = Path(args.docs)
    if path.suffix.lower() == ".jsonl":
        docs = load_docs_jsonl(path)
    else:
        documents, ids = _load_docs_with_ids(path)
        docs = [{"id": i, "text": t} for i, t in zip(ids, documents)]
    tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()] or None
    roles = [r.strip() for r in (args.roles or "").split(",") if r.strip()] or None
    filtered = filter_docs(
        docs,
        tags=tags,
        tenant=args.tenant,
        roles=roles,
    )
    if args.json:
        json.dump(filtered, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"kept {len(filtered)}/{len(docs)}")
        for d in filtered:
            tags_s = ",".join(_as_list_cli(d.get("tags")))
            acl_s = ",".join(_as_list_cli(d.get("acl")))
            print(
                f"  {d.get('id')}\ttenant={d.get('tenant', '')}\t"
                f"tags={tags_s}\tacl={acl_s}"
            )
    return 0


def _as_list_cli(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(x) for x in value]
    return [str(value)]


def cmd_chunk_ab(args: argparse.Namespace) -> int:
    sources = load_chunk_ab_sources(args.sources)
    cases = load_golden_jsonl(args.golden)
    k = max(1, int(args.k))
    report = compare_chunkers(sources, cases, k=k, retrieve_mode=args.retrieve)
    if args.json:
        json.dump(chunk_ab_report_to_dict(report), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_chunk_ab_table(report))
    return 0



def cmd_claim_check(args: argparse.Namespace) -> int:
    answer = _load_answer(args.answer)
    sources = _load_cite_sources(Path(args.sources))
    report = check_claims(
        answer,
        sources,
        supported_threshold=args.supported_threshold,
        weak_threshold=args.weak_threshold,
    )
    if args.json:
        json.dump(claim_check_report_to_dict(report), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_claim_check_report(report))
    # Fail-closed for CI: exit 1 on rewrite or abstain
    return 0 if report.decision == "pass" else 1


def cmd_conflict_check(args: argparse.Namespace) -> int:
    sources = _load_cite_sources(Path(args.sources))
    answer = None
    if getattr(args, "answer_file", None):
        answer = Path(args.answer_file).read_text(encoding="utf-8")
    elif getattr(args, "answer", None):
        answer = _load_answer(args.answer)
    report = check_conflicts(sources, answer=answer)
    if args.json:
        json.dump(conflict_report_to_dict(report), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_conflict_report(report))
    # Fail-closed for CI: exit 1 on conflict
    return 0 if report.decision == "ok" else 1


def cmd_cite_check(args: argparse.Namespace) -> int:
    answer = _load_answer(args.answer)
    sources = _load_cite_sources(Path(args.sources))
    report = verify_citation_spans(answer, sources)
    if args.json:
        json.dump(cite_span_report_to_dict(report), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_cite_span_report(report))
    # Exit 1 if unsupported quotes or orphan citations
    if report.unsupported_quotes or report.orphan_citations:
        return 1
    return 0


def cmd_position_stress(args: argparse.Namespace) -> int:
    gold = _load_answer(args.gold)
    fillers_path = Path(args.fillers)
    if fillers_path.suffix.lower() == ".jsonl":
        fillers = load_docs_jsonl(fillers_path)
    else:
        documents, ids = _load_docs_with_ids(fillers_path)
        fillers = [{"id": i, "text": t} for i, t in zip(ids, documents)]
    # Drop fillers that are the gold text or already contain it (keep offsets meaningful)
    fillers = [
        f
        for f in fillers
        if str(f.get("text") or "") != gold and gold not in str(f.get("text") or "")
    ]
    max_tokens = max(1, int(args.max_tokens))
    report = run_position_stress(gold, fillers, max_tokens=max_tokens)
    if args.json:
        json.dump(position_stress_report_to_dict(report), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_position_stress_report(report))
    return 0


def cmd_canary(args: argparse.Namespace) -> int:
    canaries = load_canaries_jsonl(args.canaries)
    path = Path(args.docs)
    if path.suffix.lower() == ".jsonl":
        docs = load_docs_jsonl(path)
    else:
        documents, ids = _load_docs_with_ids(path)
        docs = [{"id": i, "text": t} for i, t in zip(ids, documents)]
    k = max(1, int(args.k))
    report = run_canaries(canaries, docs, k=k, retrieve=args.retrieve)
    if args.json:
        json.dump(canary_report_to_dict(report), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_canary_report(report))
    return 0 if report.all_passed else 1



def cmd_html(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if args.hash_only:
        raw = path.read_text(encoding="utf-8")
        if path.suffix.lower() in {".html", ".htm"}:
            text = html_to_text(raw)
        else:
            text = raw
        print(content_hash(text))
        return 0
    doc = load_html_file(path) if path.suffix.lower() in {".html", ".htm"} else None
    if doc is None:
        # Allow hashing / text dump of non-html via html_to_text if looks like html
        raw = path.read_text(encoding="utf-8")
        text = html_to_text(raw)
        payload = {
            "id": path.stem,
            "path": str(path),
            "text": text,
            "meta": {"content_hash": content_hash(text), "content_type": "html"},
        }
    else:
        payload = {
            "id": doc.id,
            "path": doc.path,
            "text": doc.text,
            "meta": dict(doc.meta),
        }
    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"id: {payload['id']}")
        print(f"path: {payload['path']}")
        print(f"chars: {len(payload['text'])}")
        print(f"content_hash: {payload['meta'].get('content_hash', '')}")
        print("---")
        sys.stdout.write(payload["text"])
        if not str(payload["text"]).endswith("\n"):
            sys.stdout.write("\n")
    return 0



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ragpractices",
        description=(
            "Toolkit helpers for RAG chunking, ingest, hybrid search, "
            "rewrite, rerank, packing, groundedness, citations, "
            "offline eval, strategy compare, prompts, filters, "
            "HTML ingest, abstain, pipelines, quality, "
            "claim-check, conflict-check, scoring, and checklists."
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
        help="File or directory to ingest (UTF-8 .txt / .md / .html by default)",
    )
    p_ingest.add_argument(
        "--out",
        metavar="FILE",
        help="Write full corpus as JSONL to FILE",
    )
    p_ingest.add_argument(
        "--glob",
        metavar="PATTERN",
        help="Glob under a directory (default: **/*.txt, **/*.md, **/*.html)",
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
        help="End-to-end demo: rewrite → hybrid → rerank → pack → cite → ground → decide",
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


    p_eval = sub.add_parser(
        "eval",
        help="Offline retrieval eval (hit@k + MRR) against a golden JSONL set",
    )
    p_eval.add_argument(
        "--golden",
        required=True,
        help="Path to golden cases JSONL (query + expected_ids)",
    )
    p_eval.add_argument(
        "--docs",
        required=True,
        help="Docs path: hybrid-docs, corpus JSONL, or ingest directory",
    )
    p_eval.add_argument(
        "--k",
        type=int,
        default=5,
        help="hit@k cutoff / retrieval depth (default: 5)",
    )
    p_eval.add_argument(
        "--json",
        action="store_true",
        help="Emit full EvalReport as JSON",
    )
    p_eval.add_argument(
        "--min-hit-rate",
        type=float,
        default=None,
        dest="min_hit_rate",
        help="Exit 1 if hit@k rate is below this threshold",
    )
    p_eval.add_argument(
        "--min-mrr",
        type=float,
        default=None,
        dest="min_mrr",
        help="Exit 1 if mean MRR is below this threshold",
    )
    p_eval.set_defaults(func=cmd_eval)

    p_decide = sub.add_parser(
        "decide",
        help="Fail-closed answer / abstain / clarify gate",
    )
    p_decide.add_argument(
        "--top-score",
        type=float,
        default=None,
        help="Top retrieval score (optional)",
    )
    p_decide.add_argument(
        "--groundedness",
        type=float,
        default=None,
        help="Groundedness score in [0, 1] (optional)",
    )
    p_decide.add_argument(
        "--min-top-score",
        type=float,
        default=0.1,
        help="Abstain if top_score is below this (default: 0.1)",
    )
    p_decide.add_argument(
        "--min-groundedness",
        type=float,
        default=0.3,
        help="Clarify if groundedness is below this (default: 0.3)",
    )
    p_decide.add_argument(
        "--empty-retrieval",
        action="store_true",
        help="Force empty-retrieval abstain path",
    )
    p_decide.add_argument(
        "--json",
        action="store_true",
        help="Emit decision JSON",
    )
    p_decide.set_defaults(func=cmd_decide)

    p_pipe = sub.add_parser(
        "pipeline",
        help="Run a JSON-configured multi-stage pipeline with traces",
    )
    p_pipe.add_argument(
        "--config",
        required=True,
        help="Path to pipeline JSON config",
    )
    p_pipe.add_argument(
        "--query",
        required=True,
        help="Query string",
    )
    p_pipe.add_argument(
        "--docs",
        default=None,
        help="Docs path (default: examples/hybrid-docs.txt when run from repo root)",
    )
    p_pipe.add_argument(
        "--json",
        action="store_true",
        help="Emit PipelineResult as JSON",
    )
    p_pipe.set_defaults(func=cmd_pipeline)

    p_quality = sub.add_parser(
        "quality",
        help="Chunk length stats and quality flags for a docs file",
    )
    p_quality.add_argument(
        "--docs",
        required=True,
        help="Docs path: hybrid-docs, corpus JSONL, or ingest directory",
    )
    p_quality.add_argument(
        "--min-chars",
        type=int,
        default=20,
        help="Too-short / very_short threshold (default: 20)",
    )
    p_quality.add_argument(
        "--max-chars",
        type=int,
        default=4000,
        help="Too-long threshold (default: 4000)",
    )
    p_quality.add_argument(
        "--json",
        action="store_true",
        help="Emit stats + issues as JSON",
    )
    p_quality.set_defaults(func=cmd_quality)

    p_dedupe = sub.add_parser(
        "dedupe",
        help="Near-duplicate filter via token Jaccard similarity",
    )
    p_dedupe.add_argument(
        "--docs",
        required=True,
        help="Docs path: hybrid-docs, corpus JSONL, or ingest directory",
    )
    p_dedupe.add_argument(
        "--threshold",
        type=float,
        default=0.9,
        help="Jaccard threshold in [0, 1] (default: 0.9)",
    )
    p_dedupe.add_argument(
        "--json",
        action="store_true",
        help="Emit kept/dropped as JSON",
    )
    p_dedupe.set_defaults(func=cmd_dedupe)

    p_compare = sub.add_parser(
        "compare",
        help="Compare retrieval strategies (keyword / hybrid / rewrite_hybrid / hybrid_rerank)",
    )
    p_compare.add_argument(
        "--golden",
        required=True,
        help="Path to golden cases JSONL",
    )
    p_compare.add_argument(
        "--docs",
        required=True,
        help="Docs path: hybrid-docs, corpus JSONL, or ingest directory",
    )
    p_compare.add_argument(
        "--k",
        type=int,
        default=3,
        help="hit@k cutoff (default: 3)",
    )
    p_compare.add_argument(
        "--json",
        action="store_true",
        help="Emit CompareReport as JSON",
    )
    p_compare.set_defaults(func=cmd_compare)

    p_prompt = sub.add_parser(
        "prompt",
        help="Build grounded-answer or clarify prompt templates (no API calls)",
    )
    p_prompt.add_argument(
        "--question",
        required=True,
        help="User question",
    )
    p_prompt.add_argument(
        "--docs",
        default=None,
        help="Optional docs path for context (hybrid-docs / JSONL / directory)",
    )
    p_prompt.add_argument(
        "--style",
        choices=("cite", "abstain"),
        default="cite",
        help="Grounded prompt style (default: cite)",
    )
    p_prompt.add_argument(
        "--max-context-chars",
        type=int,
        default=6000,
        dest="max_context_chars",
        help="Max context characters (default: 6000)",
    )
    p_prompt.add_argument(
        "--clarify",
        action="store_true",
        help="Emit a clarify prompt instead of a grounded-answer prompt",
    )
    p_prompt.add_argument(
        "--missing",
        default="",
        help="Comma-separated missing hints for --clarify",
    )
    p_prompt.set_defaults(func=cmd_prompt)

    p_filter = sub.add_parser(
        "filter",
        help="Filter docs by tags / tenant / ACL roles (fail-closed)",
    )
    p_filter.add_argument(
        "--docs",
        required=True,
        help="Docs path: ACL JSONL preferred, or hybrid-docs / corpus JSONL",
    )
    p_filter.add_argument(
        "--tags",
        default=None,
        help="Comma-separated tags (intersection required)",
    )
    p_filter.add_argument(
        "--tenant",
        default=None,
        help="Tenant id (mismatched docs dropped)",
    )
    p_filter.add_argument(
        "--roles",
        default=None,
        help="Comma-separated caller roles/users for ACL",
    )
    p_filter.add_argument(
        "--json",
        action="store_true",
        help="Emit filtered docs as JSON",
    )
    p_filter.set_defaults(func=cmd_filter)

    p_html = sub.add_parser(
        "html",
        help="Extract text from an HTML file (and show content_hash)",
    )
    p_html.add_argument("path", help="Path to an HTML (or text) file")
    p_html.add_argument(
        "--json",
        action="store_true",
        help="Emit Document-like JSON",
    )
    p_html.add_argument(
        "--hash-only",
        action="store_true",
        dest="hash_only",
        help="Print only the sha256 content_hash",
    )
    p_html.set_defaults(func=cmd_html)


    p_chunk_ab = sub.add_parser(
        "chunk-ab",
        help="Compare chunking strategies via document-level hit@k / MRR",
    )
    p_chunk_ab.add_argument(
        "--sources",
        required=True,
        help="Source corpus: ingest directory, hybrid-docs, or JSONL",
    )
    p_chunk_ab.add_argument(
        "--golden",
        required=True,
        help="Golden JSONL with queries; expected_ids are source doc ids",
    )
    p_chunk_ab.add_argument(
        "--k",
        type=int,
        default=3,
        help="hit@k cutoff over parent docs (default: 3)",
    )
    p_chunk_ab.add_argument(
        "--retrieve",
        choices=("hybrid", "keyword"),
        default="hybrid",
        help="Retrieval over chunks (default: hybrid)",
    )
    p_chunk_ab.add_argument(
        "--json",
        action="store_true",
        help="Emit ChunkAbReport as JSON",
    )
    p_chunk_ab.set_defaults(func=cmd_chunk_ab)

    p_cite_check = sub.add_parser(
        "cite-check",
        help="Verify quoted spans and [n] markers against sources",
    )
    p_cite_check.add_argument(
        "--answer",
        required=True,
        help="Answer text or path to a file containing the answer",
    )
    p_cite_check.add_argument(
        "--sources",
        required=True,
        help="Sources path: hybrid-docs, JSONL, or JSON list",
    )
    p_cite_check.add_argument(
        "--json",
        action="store_true",
        help="Emit CiteSpanReport as JSON",
    )
    p_cite_check.set_defaults(func=cmd_cite_check)

    p_claim_check = sub.add_parser(
        "claim-check",
        help=(
            "Claim-level support + entity/number faithfulness "
            "(heuristic, not NLI)"
        ),
    )
    p_claim_check.add_argument(
        "--answer",
        required=True,
        help="Answer text or path to a file containing the answer",
    )
    p_claim_check.add_argument(
        "--sources",
        required=True,
        help="Sources path: hybrid-docs, JSONL, or JSON list",
    )
    p_claim_check.add_argument(
        "--supported-threshold",
        type=float,
        default=0.55,
        help="Overlap cutoff for supported claims (default: 0.55)",
    )
    p_claim_check.add_argument(
        "--weak-threshold",
        type=float,
        default=0.30,
        help="Overlap cutoff for weak claims (default: 0.30)",
    )
    p_claim_check.add_argument(
        "--json",
        action="store_true",
        help="Emit ClaimCheckReport as JSON",
    )
    p_claim_check.set_defaults(func=cmd_claim_check)

    p_conflict = sub.add_parser(
        "conflict-check",
        help=(
            "Pre-answer source conflict check "
            "(numbers + light negation; not NLI)"
        ),
    )
    p_conflict.add_argument(
        "--sources",
        required=True,
        help="Sources path: hybrid-docs, JSONL, or JSON list",
    )
    p_conflict.add_argument(
        "--answer",
        default=None,
        help="Optional answer text or path (notes if it sides with one camp)",
    )
    p_conflict.add_argument(
        "--answer-file",
        default=None,
        dest="answer_file",
        help="Optional path to answer file (overrides --answer)",
    )
    p_conflict.add_argument(
        "--json",
        action="store_true",
        help="Emit ConflictReport as JSON",
    )
    p_conflict.set_defaults(func=cmd_conflict_check)

    p_pos = sub.add_parser(
        "position-stress",
        help="Lost-in-the-middle stress: gold at first/middle/last (no LLM)",
    )
    p_pos.add_argument(
        "--gold",
        required=True,
        help="Gold evidence text or path to a file",
    )
    p_pos.add_argument(
        "--fillers",
        required=True,
        help="Filler docs path: hybrid-docs, JSONL, or directory",
    )
    p_pos.add_argument(
        "--max-tokens",
        type=int,
        default=512,
        dest="max_tokens",
        help="Soft token budget heuristic (default: 512)",
    )
    p_pos.add_argument(
        "--json",
        action="store_true",
        help="Emit PositionStressReport as JSON",
    )
    p_pos.set_defaults(func=cmd_position_stress)

    p_canary = sub.add_parser(
        "canary",
        help="Run index canary probes (exit 1 if any fail)",
    )
    p_canary.add_argument(
        "--canaries",
        required=True,
        help="Path to canaries JSONL (query + expected_ids)",
    )
    p_canary.add_argument(
        "--docs",
        required=True,
        help="Docs path: ACL JSONL preferred, or hybrid-docs / corpus",
    )
    p_canary.add_argument(
        "--k",
        type=int,
        default=3,
        help="hit@k cutoff (default: 3)",
    )
    p_canary.add_argument(
        "--retrieve",
        choices=("hybrid", "keyword"),
        default="hybrid",
        help="Retrieval mode (default: hybrid)",
    )
    p_canary.add_argument(
        "--json",
        action="store_true",
        help="Emit CanaryReport as JSON",
    )
    p_canary.set_defaults(func=cmd_canary)


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
