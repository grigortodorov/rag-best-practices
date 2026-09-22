# RAG Best Practices

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Practical, educational best practices for building **Retrieval-Augmented Generation (RAG)** systems.

Clear principles, tradeoffs, and patterns for chunking, retrieval, evaluation, production hardening, MCP tool-backed retrieval, and common anti-patterns. Content is honest and practical—**no fabricated metrics, stars, downloads, or eligibility claims**.

## Table of contents

1. [Who this is for](#who-this-is-for)
2. [Documentation](#documentation)
3. [Examples](#examples)
4. [Quick start mindset](#quick-start-mindset)
5. [Contributing](#contributing)
6. [License](#license)

## Who this is for

- Engineers building RAG features into products
- ML / applied AI practitioners tuning retrieval quality
- Technical leads reviewing architecture and production readiness

## Documentation

| Doc | Topic |
| --- | --- |
| [01 — Overview](docs/01-overview.md) | What RAG is and when to use it |
| [02 — Chunking](docs/02-chunking.md) | Chunking strategies and tradeoffs |
| [03 — Embeddings and retrieval](docs/03-embeddings-and-retrieval.md) | Embeddings, hybrid search, reranking |
| [04 — Evaluation](docs/04-evaluation.md) | Groundedness, retrieval metrics, offline vs online |
| [05 — Production](docs/05-production.md) | Caching, latency, cost, observability, security |
| [06 — RAG principles](docs/06-rag-principles.md) | Practical principles with examples |
| [07 — MCP tools for RAG](docs/07-mcp-tools-for-rag.md) | MCP tools in a RAG stack |
| [08 — Anti-patterns](docs/08-anti-patterns.md) | Common RAG mistakes and fixes |

## Examples

| Example | Purpose |
| --- | --- |
| [rag-principles-checklist.md](examples/rag-principles-checklist.md) | Design-review checklist |
| [mcp-tool-schemas.json](examples/mcp-tool-schemas.json) | Illustrative MCP tool definitions |
| [sample-rag-pipeline.md](examples/sample-rag-pipeline.md) | End-to-end sketch: ingest → cite |

## Quick start mindset

1. **Retrieve before generate** — do not invent private facts.
2. **Ground and cite** — answers must point to stable chunk IDs or URLs.
3. **Fail closed** — empty or low-score retrieval → abstain.
4. **Evaluate retrieval separately** from answer fluency.
5. **Prefer hybrid search** when users type IDs, error codes, or rare keywords.

For the full list, see [docs/06-rag-principles.md](docs/06-rag-principles.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to propose improvements.

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 grigortodorov.
