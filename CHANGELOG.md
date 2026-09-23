# Changelog

All notable changes to the `ragpractices` toolkit in this repository are documented here.

## [0.10.0] — 2026-09-23

### Added
- **Source conflict detector** (`ragpractices.conflict_check`): pre-answer check for disagreeing retrieved sources—**number** conflicts (similar local context / strong keyword buckets like day/percent) and lightweight **negation** polarity on shared content phrases; optional answer note when it sides with one camp; decision `ok` / `conflict` (fail-closed); CLI `ragpractices conflict-check` (exit 1 on conflict). Complements post-answer `claim_check`, `cite_spans`, aggregate `groundedness`, and index `canaries`—educational heuristic, **not** NLI / contradiction model. Example: `examples/conflict-docs.jsonl`.

### Changed
- Package version **0.10.0**.

## [0.9.0] — 2026-09-22

### Added
- **Claim-support audit** (`ragpractices.claim_check`): claim-level content-word overlap vs sources (`supported` / `weak` / `unsupported`) plus hard entity/number/date/id faithfulness; decision `pass` / `rewrite` / `abstain` (fail-closed); CLI `ragpractices claim-check` (exit 1 on rewrite/abstain). Complements aggregate `groundedness` and `cite_spans`—educational heuristic, **not** NLI.

### Changed
- Package version **0.9.0**.

## [0.8.0] — 2026-09-22

### Added
- **Chunking A/B eval** (`ragpractices.chunk_ab`): compare `fixed` / `fixed_small` / `fixed_large` / `headings` strategies with **document-level** hit@k + MRR after chunking (golden `expected_ids` are source doc ids); CLI `ragpractices chunk-ab`; example `examples/golden-chunk-ab.jsonl`.
- **Citation span verifier** (`ragpractices.cite_spans`): heuristic check of quoted spans and `[n]` / `【n】` markers vs sources (supported / unsupported quotes, unused sources, orphan citations); CLI `ragpractices cite-check`.
- **Lost-in-the-middle stress** (`ragpractices.position_stress`): pack gold evidence at first / middle / last among fillers; token estimate, gold offset, attention-risk labels (no LLM call); CLI `ragpractices position-stress`.
- **Index canaries** (`ragpractices.canaries`): query + expected ids with optional tags/tenant/roles filters; CLI `ragpractices canary` (exit 1 on failure); example `examples/canaries.jsonl`; CI canary gate after eval.

### Changed
- Package version **0.8.0**.

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
