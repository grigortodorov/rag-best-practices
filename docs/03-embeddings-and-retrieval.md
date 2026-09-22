# 03 — Embeddings, Hybrid Search, and Reranking

## Embedding models

An embedding model maps text to a dense vector so "similar meaning" is nearby in vector space.

**Selection checklist:**

- Match **language(s)** and domain of your corpus
- Prefer models with clear **context length** limits and documented training domain
- Keep **query and document** encoders consistent (same family / instructed usage)
- Plan for **re-embedding cost** when you change models (full reindex)

Store the model name and version in index metadata so you never mix incompatible vectors.

## Vector search (dense retrieval)

Approximate nearest neighbor (ANN) indexes (HNSW, IVF, etc.) trade a bit of recall for speed at scale.

- Tune `top_k` high enough for a later reranker (e.g. retrieve 20–50, keep 3–8)
- Use **metadata filters** (tenant, product, language) *before* or *with* ANN when security requires it

## Sparse / keyword search

BM25 and similar methods excel at:

- Exact IDs, error codes, SKUs, API names
- Rare proper nouns
- Short queries that are mostly keywords

Dense-only RAG often fails on these.

## Hybrid search

Combine dense + sparse scores (e.g. reciprocal rank fusion or weighted sum).

**Prefer hybrid when:**

- Users mix natural language with identifiers
- Corpus includes codes, product names, or legalese phrases
- You see "semantic" hits that miss the exact term the user typed

### Simple RRF sketch

```text
score(d) = Σ 1 / (k + rank_method_i(d))
```

Use a small constant `k` (commonly ~60). Evaluate fusion weights on your gold set rather than copying a blog default forever.

## Query rewriting

Optional step before retrieval:

- Expand acronyms known in-domain
- Split multi-intent questions
- Generate hypothetical answer embeddings (HyDE) carefully—eval required; can drift

Keep rewrites **logged** for debugging.

## Reranking

A cross-encoder or LLM reranker scores (query, chunk) pairs more accurately than bi-encoder similarity alone.

Typical pattern:

1. Cheap retrieve (hybrid) → many candidates
2. Rerank → small set for the prompt

Watch **latency and cost**; cache when queries repeat.

## Context packing

After retrieval:

- Deduplicate near-identical chunks
- Respect token budget; prefer diversity across documents when appropriate
- Preserve citation handles (`chunk_id`, URL, section)
- Drop chunks below a score threshold instead of padding the window

## Anti-patterns (retrieval-specific)

- One huge "document embedding" with no chunking for long manuals
- Ignoring keyword search for support/IT corpora
- Stuffing low-score chunks until the context window is full
- Changing embedding models without reindexing

See also [08 — Anti-patterns](08-anti-patterns.md).

## Next

- [04 — Evaluation](04-evaluation.md)
