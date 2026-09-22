# 11 — FAQ

Short answers to questions that come up when building RAG systems. Deeper treatment lives in the linked docs.

## General

### Do I always need a vector database?

No. If the corpus fits in context, stuffing or simple keyword search may be enough. Use a vector (or hybrid) index when the corpus is large, changes often, or you need semantic recall beyond exact keywords. See [01 — Overview](01-overview.md).

### Dense search or hybrid?

Start with **hybrid** (dense + BM25/keyword) when users type IDs, error codes, SKUs, or rare proper nouns. Dense-only systems routinely miss those. See [03 — Embeddings and retrieval](03-embeddings-and-retrieval.md).

### How big should chunks be?

There is no universal number. A common starting band for prose is **256–512 tokens** with small overlap, after structure-aware splits. Tune with retrieval eval. Tables, code, and FAQs need different shapes—see [02 — Chunking](02-chunking.md) and [examples/chunking-heuristics.md](../examples/chunking-heuristics.md).

## Grounding and safety

### What should happen when retrieval returns nothing?

**Fail closed:** abstain or say no matching sources were found. Do not invent private facts. See [06 — RAG principles](06-rag-principles.md) and [09 — Citations and grounding](09-citations-and-grounding.md).

### Are citations enough to prevent hallucination?

No. Citations help auditability, but models can still cite irrelevant chunks or paraphrase incorrectly. Combine grounding prompts, fail-closed retrieval, citation validation, and eval ([09](09-citations-and-grounding.md), [04](04-evaluation.md)).

### Can retrieved docs prompt-inject my agent?

Yes. Treat chunk text as **untrusted**. Delimit context, allowlist tools, and authorize on the server—never let wiki text alone escalate privileges. See [05 — Production](05-production.md) and [07 — MCP tools](07-mcp-tools-for-rag.md).

## Evaluation and ops

### What is the smallest useful eval set?

Often **50–200** labeled questions spanning happy path, keyword/ID queries, and **unanswerable** cases, against a frozen corpus snapshot. Track retrieval (e.g. Recall@k) separately from groundedness. See [04 — Evaluation](04-evaluation.md) and [examples/evaluation-rubric.md](../examples/evaluation-rubric.md).

### Why did quality drop after we changed the embedding model?

Mixing embedder versions in one index produces nonsense neighbors. Version the index and **fully rebuild** on embedder change ([08 — Anti-patterns](08-anti-patterns.md)).

### How do we keep answers fresh when docs change?

Versioned ingest, event-driven or scheduled reindex, cache invalidation tied to document versions, and show `updated_at` in citations when freshness matters ([05 — Production](05-production.md)).

## Multimodal and messy formats

### Our PDFs retrieve garbage. Is the embedder broken?

Often the **extractor/OCR** is broken. Fix reading order, tables, and header/footer noise before tuning models ([10 — Multimodal and tables](10-multimodal-and-tables.md)).

### How should we chunk tables?

Prefer row- or small row-group chunks with **headers repeated**, or keep small tables intact under a section. Dual text + structured storage helps exact lookups ([10](10-multimodal-and-tables.md)).

## MCP / tools

### When should retrieval be an MCP tool?

When multiple clients share backends, you need get-by-id / list-collections, or live systems that are not fully embedded. Harden auth and allowlists. See [07 — MCP tools for RAG](07-mcp-tools-for-rag.md) and [examples/mcp-tool-schemas.json](../examples/mcp-tool-schemas.json).

### Can the model invent document ids?

It will try—**don’t allow it**. Only use ids returned by tools; validate arguments server-side.

## Computer use (browser / desktop agents)

### Should we use a computer-use agent instead of RAG?

No—they solve different problems. **RAG** answers from indexed docs; **computer use** operates a live UI. Prefer typed MCP/API tools when they exist; use computer use for UI-only gaps (form flows, deploy verification). Combine them by retrieving a runbook first, then executing steps under allowlists and human confirmation for destructive actions. See [12 — Computer-use tools](12-computer-use-tools.md) and [examples/computer-use-checklist.md](../examples/computer-use-checklist.md).

### Is it OK for the agent to read passwords or API keys from the screen?

No. Do not scrape secrets from screenshots into prompts or logs. Inject credentials server-side or via a vault/browser store, confirm destructive actions, and enforce host/app allowlists ([12](12-computer-use-tools.md), [05](05-production.md)).

## Process

### Where should I propose a doc fix?

Open an issue with the [doc improvement template](../.github/ISSUE_TEMPLATE/doc-improvement.yml) or a PR. See [CONTRIBUTING.md](../CONTRIBUTING.md).

### Is this repo affiliated with a vendor score or badge program?

No. Content is educational. Do not add fabricated stars, downloads, dependents, or eligibility claims ([CONTRIBUTING.md](../CONTRIBUTING.md)).

## Next

- [01 — Overview](01-overview.md)
- [08 — Anti-patterns](08-anti-patterns.md)
- [12 — Computer-use tools](12-computer-use-tools.md)
- [examples/rag-principles-checklist.md](../examples/rag-principles-checklist.md)
- [examples/computer-use-checklist.md](../examples/computer-use-checklist.md)
