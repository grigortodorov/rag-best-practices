# RAG Principles Checklist

Use this in design reviews or before shipping a RAG change.

Related: [docs/06-rag-principles.md](../docs/06-rag-principles.md) · [docs/09-citations-and-grounding.md](../docs/09-citations-and-grounding.md) · [docs/08-anti-patterns.md](../docs/08-anti-patterns.md) · [evaluation-rubric.md](evaluation-rubric.md) · [sample-rag-pipeline.md](sample-rag-pipeline.md)

## Retrieval

- [ ] Retrieval (or equivalent tool call) runs **before** factual generation
- [ ] Hybrid search enabled when users query IDs, codes, or rare keywords
- [ ] `top_k` and score threshold documented; empty/low-score path **fails closed**
- [ ] Chunking tuned against real questions, not only file format
- [ ] Metadata filters (tenant/ACL/product/language) applied at retrieve time
- [ ] Near-duplicate chunks deduped before packing context

## Grounding and citations

- [ ] Prompt requires answers to be grounded in provided context
- [ ] Abstain behavior defined when context is insufficient
- [ ] Responses include stable citations (`chunk_id` / URL / section)
- [ ] Citations are verified spot-checked on the eval set
- [ ] Retrieved text treated as **untrusted** (delimited; no privileged tools from chunk text alone)

## Evaluation

- [ ] Retrieval metrics (e.g. Recall@k, MRR) tracked separately from answer quality
- [ ] Gold set includes keyword/ID and **unanswerable** queries
- [ ] Index, embedder, chunker, and prompt versions recorded per eval run
- [ ] Failure analysis distinguishes corpus miss vs retrieve miss vs generate ignore

## Production

- [ ] Audit trail: query id → retrieved chunks/scores → model / prompt / index versions
- [ ] Tenant/ACL filters enforced at retrieve time
- [ ] PII minimization / redaction considered for the index
- [ ] Tool allowlists and no secrets in tool arguments (if using MCP/tools)
- [ ] Cache invalidation tied to document version bumps
- [ ] Latency budget broken down (embed / retrieve / rerank / generate)
- [ ] Index rollback / canary plan documented

## MCP / tool-backed retrieval (if applicable)

- [ ] `search_docs` (or equivalent) required before corpus answers
- [ ] Model cannot invent `document_id` values
- [ ] `list_collections` results respect caller authorization
- [ ] Schemas validate enums, max lengths, and `top_k` caps
- [ ] Example schemas reviewed: [mcp-tool-schemas.json](mcp-tool-schemas.json)

## Sign-off

| Item | Owner | Date |
| --- | --- | --- |
| Retrieval eval gate | | |
| Groundedness review | | |
| Security review | | |
| Production readiness | | |
