# 02 — Chunking Strategies and Tradeoffs

Chunking splits source documents into units that are indexed and retrieved. Bad chunks are a common root cause of weak RAG.

## Goals of a good chunk

- **Self-contained enough** to answer or support an answer without the whole document
- **Small enough** to keep noise low and fit many candidates in context
- **Large enough** to preserve necessary local context (definitions, preceding clauses)
- **Stable IDs** so you can cite and audit what was retrieved

## Common strategies

### Fixed-size windows (tokens or characters)

Split every N tokens, often with overlap.

- **Pros:** Simple, predictable index size
- **Cons:** Cuts mid-sentence or mid-table; overlap helps but wastes storage

**When:** Homogeneous text (blogs, plain policies) and you need a baseline fast.

### Structure-aware (headings, paragraphs, sections)

Split on Markdown headings, HTML sections, or paragraph boundaries.

- **Pros:** Aligns with how humans authored meaning
- **Cons:** Section length varies wildly; long sections may need secondary splits

**When:** Docs with clear outline structure (wikis, manuals).

### Semantic / topic splits

Detect topic shifts (embedding similarity drops) and cut there.

- **Pros:** Can group related sentences across weak formatting
- **Cons:** Harder to tune; less deterministic; more compute at ingest

**When:** Messy prose without reliable headings.

### Recursive / hierarchical

Keep parent sections and child chunks; retrieve children, expand to parents if needed.

- **Pros:** Better context expansion; supports "zoom out"
- **Cons:** More complex indexing and citation paths

**When:** Long technical docs where a paragraph alone is incomplete.

### Special content

| Content | Tip |
| --- | --- |
| Tables | Prefer row- or section-level chunks with header context repeated |
| Code | Chunk by function/class; keep signatures and docstrings together |
| FAQs | One Q+A pair per chunk |
| PDFs | Fix extraction noise before clever chunking |

## Overlap

Overlap (e.g. 10–20% of chunk size) reduces boundary misses. Too much overlap duplicates hits and confuses citations. Prefer structure-aware cuts over large blind overlap when possible.

## Metadata to store with each chunk

- `document_id`, `chunk_id`, `title` / section path
- Source URI or path, version or `updated_at`
- Optional: ACL / tenant id, language, content type

Metadata enables filtering, citations, and security later.

### Example chunk record

```json
{
  "document_id": "policies/refunds.md",
  "chunk_id": "policies/refunds.md:chunk-12",
  "section_path": "Refunds > Window",
  "text": "Customers may request a refund within 30 days of purchase.",
  "updated_at": "2026-01-15T10:00:00Z",
  "tenant_id": "acme",
  "embedder": "text-embedding-example/v1"
}
```

## Practical defaults (starting point, not gospel)

- Start with **structure-aware** splits, then **max token cap** (e.g. 256–512 tokens) with small overlap
- See [examples/chunking-heuristics.md](../examples/chunking-heuristics.md) for size/overlap starting points by content type
- Tune using **retrieval eval** (see [04-evaluation.md](04-evaluation.md)), not gut feel alone
- Chunk for the **questions users ask**, not only for document type
- Revisit chunking when Recall@k plateaus but humans say "the answer is in the doc"

## Next

- [examples/chunking-heuristics.md](../examples/chunking-heuristics.md)
- [10 — Multimodal and tables](10-multimodal-and-tables.md)
- [03 — Embeddings and retrieval](03-embeddings-and-retrieval.md)
- [08 — Anti-patterns](08-anti-patterns.md)
