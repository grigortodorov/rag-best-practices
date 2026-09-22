# 13 — Usable toolkit (`ragpractices`)

A small, stdlib-first Python package that ships with this repo. It does **not** call remote APIs and does not require API keys. Use it to practice document ingest, chunking, hybrid (keyword + dense) search, query rewrite / multi-query, deterministic rerank / MMR, context packing, heuristic groundedness checks, citation formatting, offline retrieval eval, fail-closed abstain/clarify, configurable pipelines with traces, chunk quality / near-dedupe, answer scoring, and a design-review checklist.

Related: [02 — Chunking](02-chunking.md) · [03 — Embeddings and retrieval](03-embeddings-and-retrieval.md) · [04 — Evaluation](04-evaluation.md) · [06 — RAG principles](06-rag-principles.md) · [examples/evaluation-rubric.md](../examples/evaluation-rubric.md)

## Install

From the repository root (editable):

```bash
pip install -e .
ragpractices --help
```

Optional dev extra for pytest:

```bash
pip install -e ".[dev]"
```

Requires Python 3.10+. Package name: `ragpractices` (version `0.6.0+`). GitHub Actions CI runs `unittest` on push/PR to `main`.

## Library API

Import name: `ragpractices`.

```python
from ragpractices import (
    __version__,
    Document,
    load_text_file,
    load_markdown_file,
    load_path,
    corpus_to_hybrid_docs,
    save_corpus_jsonl,
    load_corpus_jsonl,
    chunk_text,
    chunk_by_headings,
    keyword_score,
    normalize_scores,
    reciprocal_rank_fusion,
    hybrid_search,
    rewrite_query,
    multi_query,
    rerank,
    mmr_rerank,
    PackResult,
    estimate_tokens,
    pack_context,
    truncate_to_tokens,
    GroundednessReport,
    check_groundedness,
    Citation,
    format_inline_citations,
    build_sources_block,
    attach_citations,
    GoldenCase,
    EvalReport,
    hit_at_k,
    mrr,
    evaluate_retrieval,
    load_golden_jsonl,
    AbstainResult,
    should_answer,
    PipelineResult,
    load_pipeline_config,
    run_pipeline,
    ChunkStats,
    chunk_stats,
    flag_chunks,
    dedupe_near,
    score_answer,
    format_scorecard,
    get_checklist,
    DIMENSIONS,
)
```

### Document ingest

Load local UTF-8 `.txt` / `.md` files into a small corpus, optionally strip Markdown YAML front matter, and serialize as JSONL.

#### `Document`

Dataclass with fields: `id` (str), `path` (str), `text` (str), `meta` (dict).

#### `load_text_file(path) -> Document`

Reads UTF-8 text. `id` is the file stem (or a path relative to the directory root when loaded via `load_path`).

#### `load_markdown_file(path) -> Document`

Same as text, but a leading `---` … `---` YAML front-matter block is stripped into `meta` (flat `key: value` lines only).

#### `load_path(path, *, glob=None) -> list[Document]`

File or directory. Directory default globs: `**/*.txt` and `**/*.md`. Skips hidden paths and common folders (`.venv`, `venv`, `__pycache__`, `node_modules`, …). Custom `--glob` / `glob=` overrides the default patterns.

#### `corpus_to_hybrid_docs(docs) -> list[str]`

Plain text list for `hybrid_search`.

#### `save_corpus_jsonl(docs, path)` / `load_corpus_jsonl(path)`

One JSON object per line (`id`, `path`, `text`, `meta`).

```python
from ragpractices import load_path, corpus_to_hybrid_docs, hybrid_search

docs = load_path("examples/ingest-sample")
hits = hybrid_search("refund shipping", corpus_to_hybrid_docs(docs), fusion="rrf")
```

### `chunk_text(text, chunk_size=800, overlap=100) -> list[str]`

Fixed-size character windows with overlap. Empty / whitespace-only input returns `[]`. Raises `ValueError` if `chunk_size <= 0` or if overlap is not in `[0, chunk_size)`.

### `chunk_by_headings(markdown, max_chars=1200) -> list[dict]`

Splits on ATX Markdown headings (`#` … `######`). Each item is `{"text": str, "heading": str}`. A preamble before the first heading uses `heading=""`. Oversized sections are further split with `chunk_text`.

### Hybrid search stubs

Educational helpers for sparse/dense fusion. Deterministic; no embeddings library.

#### `keyword_score(query, documents) -> list[float]`

Casefold alphanumeric tokenization. BM25-lite: document term frequency × IDF-ish (`log((N+1)/(df+1)) + 1`).

#### `normalize_scores(scores) -> list[float]`

Min-max to `[0, 1]`. Empty → `[]`; constant inputs → zeros (same length).

#### `reciprocal_rank_fusion(rank_lists, k=60) -> list[tuple[int, float]]`

RRF over ranked document index lists (best first). Returns `(doc_index, score)` sorted by score descending.

#### `hybrid_search(query, documents, dense_scores=None, *, rrf_k=60, alpha=0.5, fusion="rrf"|"weighted") -> list[dict]`

Builds sparse ranks from `keyword_score` and dense ranks from `dense_scores` (zeros if `None`). Modes:

- `fusion="rrf"` — RRF over sparse + dense ranks
- `fusion="weighted"` — `alpha * norm(dense) + (1 - alpha) * norm(sparse)`

Each result: `{"index", "score", "document"}`, best first.

```python
from ragpractices import hybrid_search

docs = [
    "Refund within 30 days.",
    "Shipping takes 5-7 days.",
    "Password reset expires in 15 minutes.",
]
hits = hybrid_search("refund shipping", docs, fusion="rrf")
# → ranked list; keyword overlap prefers refund/shipping docs
```

### Query rewrite stubs

Deterministic heuristics (no LLM). Modes: `expand`, `clarify`, `hyphenate_split`.

#### `rewrite_query(query, *, mode="expand") -> dict`

Returns `original`, `rewritten`, `mode`, `notes`. Expand also includes `keywords` (stopword-trimmed).

- **expand** — keep original tokens and add synonym-ish expansions for common ops words (`refund`↔`return`, `ship`/`shipping`↔`delivery`, `password`↔`auth`/`authentication`)
- **clarify** — if the query has fewer than 4 tokens, append `(looking for policy details)`; otherwise return the cleaned query
- **hyphenate_split** — split `camelCase`, hyphenated, and underscored tokens

#### `multi_query(query) -> list[str]`

Returns 2–3 deduplicated variants: cleaned original, expand rewrite, and a keyword-only join — handy for multi-query retrieval demos.

```python
from ragpractices import rewrite_query, multi_query

rewrite_query("refund ship", mode="expand")
# → rewritten includes return/delivery; keywords list without stopwords

multi_query("refund ship")
# → ["refund ship", "refund return … ship shipping delivery", "refund return …"]
```

### Rerank stubs

#### `rerank(query, documents, *, scores=None, top_k=None) -> list[dict]`

Blends normalized keyword-overlap with the query and optional incoming scores (`0.5 / 0.5` when scores are provided). Each result: `{"index", "score", "document"}`, best first.

#### `mmr_rerank(query, documents, *, lambda_mult=0.7, top_k=5) -> list[dict]`

Simple Maximal Marginal Relevance using token Jaccard as similarity (deterministic). Higher `lambda_mult` favors relevance over diversity.

```python
from ragpractices import rerank, mmr_rerank

docs = ["Refund within 30 days.", "Shipping 5-7 days.", "Password reset."]
rerank("refund", docs, top_k=2)
mmr_rerank("refund shipping", docs, lambda_mult=0.7, top_k=2)
```


### Context packing / token budget

Educational packing helpers. Token estimates use **~4 characters per token** (not a real tokenizer).

#### `estimate_tokens(text) -> int`

`ceil(len(text) / 4)`; empty/whitespace → `0`.

#### `truncate_to_tokens(text, max_tokens) -> str`

Hard character cap at `max_tokens * 4`.

#### `pack_context(docs, *, max_tokens, separator="\n\n---\n\n", preserve_order=True, truncate=False) -> PackResult`

Greedily packs strings or dicts (`text` / optional `id`, `score`) under a budget. Oversized docs are skipped unless `truncate=True` (then the last partial may be truncated). `preserve_order=False` sorts by `score` descending first.

`PackResult`: `packed_text`, `included`, `omitted`, `estimated_tokens`, `max_tokens`.

```python
from ragpractices import pack_context, estimate_tokens

docs = ["Refund within 30 days.", "Shipping takes 5-7 days.", "Password reset."]
result = pack_context(docs, max_tokens=20)
print(result.included, result.estimated_tokens)
```

### Groundedness check stub

Heuristic word-overlap check (**not** a production NLI / entailment judge). Related: [09 — Citations and grounding](09-citations-and-grounding.md) · [04 — Evaluation](04-evaluation.md).

#### `check_groundedness(answer, sources, *, min_overlap=0.0) -> GroundednessReport`

Lowercases alphanumeric tokens, drops a light stopword list, and reports the fraction of unique answer content words found in the union of source texts. Also lists per-source overlap and unsupported answer sentences (low sentence-level overlap).

`GroundednessReport`: `score` (0–1), `supported_word_ratio`, `unsupported_sentences`, `per_source`, `notes`.

```python
from ragpractices import check_groundedness

report = check_groundedness(
    "Refunds are within 30 days.",
    ["Refund requests are accepted within 30 days of purchase."],
)
print(report.score, report.unsupported_sentences)
```

### Citation formatter

Helpers to format grounded answers with inline citations and a Sources appendix. Related: [09 — Citations and grounding](09-citations-and-grounding.md).

#### `Citation`

Dataclass: `id`, optional `title` / `snippet` / `score` / `meta`. `Citation.from_dict(...)` accepts loose retrieved dicts (`id`/`index`, `document`/`text`).

#### `format_inline_citations(answer, sources, *, style="numeric"|"bracketed") -> str`

- **numeric** — replace `[n]` with `(n)`; if no markers, append `(1) (2) …`
- **bracketed** — replace `[@id]` with `[id]`; if none, append `[id]` for each source

#### `build_sources_block(sources, *, style="numeric") -> str`

Renders a `Sources:` appendix (`(1) title — snippet` or `[id] …`).

#### `attach_citations(answer, retrieved, *, style="numeric") -> dict`

Returns `{"answer", "sources_block", "full_text"}`.

```python
from ragpractices import attach_citations

retrieved = [
    {"id": "doc-0", "document": "Refund within 30 days.", "score": 0.9},
    {"id": "doc-1", "text": "Shipping takes 5-7 days."},
]
attach_citations("Refunds are within 30 days [1].", retrieved, style="numeric")
```

### `score_answer(scores: dict[str, int]) -> dict`

Dimensions (each `0` / `1` / `2`):

| Key | Meaning (spirit of the eval rubric) |
| --- | --- |
| `groundedness` | Claims supported by retrieved context |
| `relevance` | Answer addresses the question |
| `completeness` | Covers the asked point given available context |
| `citation_quality` | Citations present, real, and claim-aligned |

Returns `scores`, `total`, `max` (8), `passed`, and `gate_failures`. **Pass gate:** `groundedness >= 1` (fail closed on fully unsupported answers). Missing/unknown dimensions or out-of-range values raise `ValueError`.

### `format_scorecard(result) -> str`

Plain-text scorecard for humans or logs.

### `get_checklist() -> str`

Short embedded principles checklist (full checklist lives in `examples/rag-principles-checklist.md`).

### Offline retrieval eval

Educational hit@k and MRR against a golden set. **Not** a substitute for human judgment or production metrics.

- `hit_at_k(retrieved_ids, expected_ids, k) -> bool`
- `mrr(retrieved_ids, expected_ids) -> float`
- `evaluate_retrieval(cases, retrieve_fn, *, k=5) -> EvalReport`
- `load_golden_jsonl(path) -> list[GoldenCase]`

### Fail-closed abstain

- `should_answer(*, top_score=None, groundedness=None, min_top_score=0.1, min_groundedness=0.3, empty_retrieval=False) -> AbstainResult`
- Decisions: `answer` | `abstain` | `clarify`

### Pipeline config + traces

- `load_pipeline_config(path) -> dict`
- `run_pipeline(config, *, query, docs) -> PipelineResult` with ordered stage traces (`name`, `ms`, `ok`, `summary`)
- Stages: `rewrite`, `hybrid`, `rerank`, `pack`, `ground`, `cite`, `decide` (see `examples/pipeline.json`)

### Chunk quality + near-dup

- `chunk_stats(texts) -> ChunkStats`
- `flag_chunks(texts, *, min_chars=20, max_chars=4000) -> list[ChunkIssue]`
- `dedupe_near(texts, *, threshold=0.9) -> DedupeResult`

## CLI

Entry point: `ragpractices`.

### Chunk a file to JSON

```bash
ragpractices chunk examples/sample.txt --chunk-size 120 --overlap 20
ragpractices chunk examples/sample.txt --by-headings --max-chars 200
```

### Hybrid search over a docs file

Documents in the file are separated by a line containing only `---` (i.e. `\n---\n`).

```bash
ragpractices hybrid "refund shipping" --docs examples/hybrid-docs.txt --fusion rrf --top 3
ragpractices hybrid "shipping" --docs examples/hybrid-docs.txt --fusion weighted --alpha 0.0 --top 2
```

Optional `--dense path.json` supplies a JSON list of floats (same length as documents). `--alpha` applies to weighted fusion; `--rrf-k` to RRF.

### Ingest a file or directory

Default prints a short summary table (`id`, `chars`, `path`). Use `--out` for a full JSONL corpus; `--stdout` for JSONL on stdout.

```bash
ragpractices ingest examples/ingest-sample
ragpractices ingest examples/ingest-sample --out /tmp/corpus.jsonl
ragpractices ingest examples/ingest-sample --glob '**/*.md' --stdout
```

### Rewrite a query / multi-query

```bash
ragpractices rewrite "refund ship" --mode expand
ragpractices rewrite "refund" --mode clarify
ragpractices rewrite "orderID password-reset" --mode hyphenate_split
ragpractices rewrite "refund ship" --multi
```

### Rerank documents

Same docs file format as hybrid (`---` separators):

```bash
ragpractices rerank "refund" --docs examples/hybrid-docs.txt --top 3
ragpractices rerank "refund shipping" --docs examples/hybrid-docs.txt --mmr --top 3
```

### Attach citations

`--answer` may be literal text or a file path. `--sources` accepts JSONL (`id` + `text`), a JSON list, or a hybrid-docs file (ids generated as `doc-0`, …).

```bash
ragpractices cite --answer "Refunds are within 30 days [1]." \
  --sources examples/hybrid-docs.txt --style numeric
ragpractices cite --answer "See the policy." --sources /tmp/corpus.jsonl \
  --style bracketed --json
```


### Pack context under a token budget

Docs file formats match `cite` (JSONL / JSON / `---` separated). Packed text goes to stdout; a JSON summary of included/omitted tokens goes to stderr.

```bash
ragpractices pack --docs examples/hybrid-docs.txt --max-tokens 40
ragpractices pack --docs examples/hybrid-docs.txt --max-tokens 20 --truncate
```

### Heuristic groundedness check

```bash
ragpractices ground --answer "Refunds are within 30 days." \
  --sources examples/hybrid-docs.txt
ragpractices ground --answer "We ship unicorns tomorrow." \
  --sources examples/hybrid-docs.txt --json
```


### Offline retrieval eval

```bash
ragpractices eval --golden examples/golden-retrieval.jsonl \
  --docs examples/hybrid-docs.txt --k 3
```

### Fail-closed decide

```bash
ragpractices decide --top-score 0.05 --groundedness 0.2
ragpractices decide --top-score 0.8 --groundedness 0.9
```

### Configurable pipeline

```bash
ragpractices pipeline --config examples/pipeline.json --query "refund shipping"
```

### Chunk quality and near-dedupe

```bash
ragpractices quality --docs examples/hybrid-docs.txt
ragpractices dedupe --docs examples/hybrid-docs.txt --threshold 0.9
```

### End-to-end demo

Runs rewrite → hybrid → rerank → pack → cite → ground → decide against sample docs (defaults to `examples/hybrid-docs.txt` when run from the repo root). Also available as `examples/e2e_demo.py`.

```bash
ragpractices demo --query "refund shipping" --max-tokens 200
PYTHONPATH=src python examples/e2e_demo.py
```

### Score an answer

```bash
ragpractices score --scores groundedness=2,relevance=2,completeness=1,citation_quality=2
```

Omit `--scores` to enter values interactively. Exit code `0` on PASS, `1` on FAIL (gate), `2` on usage/IO errors.

### Print checklist

```bash
ragpractices checklist
```

## Tests

No runtime test dependency. From the repo root:

```bash
python -m unittest discover -s tests -v
```

With the optional `dev` extra:

```bash
pytest -q
```

## Scope and honesty

This toolkit is intentionally small: local document ingest, character/heading chunking, hybrid search / rewrite / rerank / packing / groundedness *stubs* (not a production retriever or NLI judge), offline hit@k/MRR helpers, a fail-closed abstain gate, a JSON pipeline runner with traces, chunk quality / Jaccard near-dedupe, citation formatting helpers, and a four-dimension scorecard. It is **not** an embedder or full benchmark suite. Do not treat demo scores as product metrics; extend the golden set and retrieval metrics as described in [04 — Evaluation](04-evaluation.md).

## Next

- [examples/sample.txt](../examples/sample.txt) — tiny fixture for the chunk CLI
- [examples/hybrid-docs.txt](../examples/hybrid-docs.txt) — tiny fixture for the hybrid CLI
- [examples/ingest-sample/](../examples/ingest-sample/) — tiny multi-file fixture for the ingest CLI
- [examples/e2e_demo.py](../examples/e2e_demo.py) — runnable end-to-end pipeline demo
- [examples/evaluation-rubric.md](../examples/evaluation-rubric.md) — fuller human + auto rubric
- [examples/rag-principles-checklist.md](../examples/rag-principles-checklist.md) — full design-review checklist
