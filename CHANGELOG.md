# Changelog

All notable changes to the `ragpractices` toolkit in this repository are documented here.

## [0.7.0] — 2026-09-22

### Added
- **Strategy compare** (`ragpractices.compare`): run golden cases through `keyword`, `hybrid`, `rewrite_hybrid`, and `hybrid_rerank`; CLI `ragpractices compare`.
- **Grounded prompt templates** (`ragpractices.prompts`): `build_grounded_prompt` / `build_clarify_prompt` (templates only, no API calls); CLI `ragpractices prompt`.
- **Metadata / ACL filters** (`ragpractices.filters`): fail-closed `filter_docs` by tags, tenant, and roles; CLI `ragpractices filter`; optional `filter` key on pipeline configs; example `examples/acl-docs.jsonl`.
- **HTML ingest + content hashing** (`ragpractices.html_ingest` / `ingest.content_hash`): `html_to_text`, `load_html_file`, stable sha256 `content_hash`; `ragpractices ingest` accepts `.html`; CLI `ragpractices html`; example `examples/ingest-sample/faq.html`.
- **Eval CI gate**: `ragpractices eval --min-hit-rate` / `--min-mrr` (exit 1 on failure); workflow runs a 0.6 hit@k gate.
- Expanded `examples/golden-retrieval.jsonl` and new `examples/golden-retrieval-hard.jsonl`.

### Changed
- Package version **0.7.0**.
- Document ingest attaches `content_hash` in `meta` by default.

## [0.6.0] — 2026-09

### Added
- Offline retrieval eval (`hit_at_k`, `mrr`, `evaluate_retrieval`, golden JSONL).
- Fail-closed abstain / clarify (`should_answer`).
- Configurable multi-stage pipeline with traces (`run_pipeline`).
- Chunk quality stats, flags, and near-dedupe (`quality`).
- Context packing under a token budget (`packing`).
- Heuristic groundedness checks (`groundedness`).
- End-to-end `ragpractices demo` and richer CLI surface.

## [0.5.0] — 2026-09

### Added
- Query rewrite / multi-query stubs (`rewrite`).
- Keyword blend + MMR rerank stubs (`rerank`).
- Citation formatting helpers (`citations`).
- Document ingest for `.txt` / `.md` with JSONL corpus I/O.

## [0.2.0] — earlier

### Added
- Initial installable toolkit: chunking, hybrid search stubs, answer rubric, principles checklist, CLI entry point.

## [0.1.0] — earlier

### Added
- Documentation-first RAG best-practices repo (chunking, retrieval, eval, production, MCP, anti-patterns).
