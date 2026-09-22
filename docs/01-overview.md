# 01 — Overview: What RAG Is and When to Use It

## What is RAG?

Retrieval-Augmented Generation (RAG) combines a **retriever** with a **generator** (usually an LLM):

1. The user asks a question.
2. The system retrieves relevant passages from a knowledge base (documents, tickets, code, APIs).
3. The LLM generates an answer **conditioned on** those passages (and the question).

The goal is to ground answers in up-to-date or proprietary data without training a new model for every content change.

## Core loop

```text
Query → (optional rewrite) → Retrieve top-k chunks → (optional rerank)
    → Build prompt with citations → Generate → Return answer + sources
```

Ingest is the other half of the system:

```text
Sources → Extract/clean → Chunk + metadata → Embed → Index (dense ± sparse)
```

## When RAG helps

Use RAG when you need one or more of:

- **Private or proprietary knowledge** the base model was never trained on
- **Fresh content** that changes faster than you can fine-tune
- **Citations / auditability** — answers should point to source passages
- **Domain corpora** (policies, manuals, wikis) that are too large for a single prompt

## When RAG is a weak fit

Prefer other approaches when:

- The task is pure reasoning or style with **no external facts** needed
- The corpus is tiny and always fits in the context window (simple stuffing may be enough)
- You need **guaranteed** exact answers from structured systems of record — use APIs/tools or SQL, optionally alongside RAG
- Latency or cost budgets cannot support retrieval + generation on every request (consider caching, smaller models, or non-LLM search)

## Design choices that matter early

| Choice | Why it matters |
| --- | --- |
| Chunking | Wrong size/boundaries hurt recall and citation quality |
| Embedding + index | Defines semantic recall; hybrid often needed for IDs/keywords |
| Prompt grounding | Model must be instructed to use only retrieved context |
| Evaluation | Separate retrieval quality from generation quality |
| Failure mode | Empty or low-confidence retrieval should fail closed |

## Suggested reading order

1. This overview
2. [02 — Chunking](02-chunking.md) and [03 — Embeddings and retrieval](03-embeddings-and-retrieval.md)
3. [06 — RAG principles](06-rag-principles.md) + [examples/rag-principles-checklist.md](../examples/rag-principles-checklist.md)
4. [04 — Evaluation](04-evaluation.md) before claiming quality
5. [05 — Production](05-production.md) and [08 — Anti-patterns](08-anti-patterns.md)
6. [07 — MCP tools](07-mcp-tools-for-rag.md) if you expose retrieval as tools

## Next

- [02 — Chunking](02-chunking.md)
- [06 — RAG principles](06-rag-principles.md)
- [examples/sample-rag-pipeline.md](../examples/sample-rag-pipeline.md)
