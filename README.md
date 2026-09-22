# RAG Best Practices

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Practical, educational guidance for building Retrieval-Augmented Generation (RAG) systems that stay grounded, measurable, and production-safe.**

This repo collects clear principles, tradeoffs, and patterns—chunking, hybrid retrieval, evaluation, citations, multimodal/PDF pitfalls, MCP tool-backed search, computer-use agents alongside RAG, and common anti-patterns. Content is honest and hands-on: **no fabricated metrics, stars, downloads, dependents, or vendor eligibility claims**.

Use it as a design-review companion, an onboarding reading path, or a checklist source when shipping RAG features.

## Table of contents

1. [Who this is for](#who-this-is-for)
2. [Documentation](#documentation)
3. [Examples](#examples)
4. [Quick start mindset](#quick-start-mindset)
5. [Contributing](#contributing)
6. [Code of conduct](#code-of-conduct)
7. [License](#license)

## Who this is for

- **Engineers** building RAG features into products (search + LLM answer UIs, internal assistants)
- **ML / applied AI practitioners** tuning chunking, embeddings, hybrid retrieval, and eval harnesses
- **Technical leads** reviewing architecture, grounding, ACLs, and production readiness
- **Builders using tool-calling / MCP** who want retrieval behind typed tools with fail-closed behavior

Familiarity with basic LLM apps helps; you do not need a research background.

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
| [09 — Citations and grounding](docs/09-citations-and-grounding.md) | Citation formats, grounded answers, missing context |
| [10 — Multimodal and tables](docs/10-multimodal-and-tables.md) | PDFs, tables, images, OCR, structure-aware chunking |
| [11 — FAQ](docs/11-faq.md) | Short answers to common build questions |
| [12 — Computer-use tools](docs/12-computer-use-tools.md) | Browser/desktop agents with RAG workflows |

**Suggested path:** [01](docs/01-overview.md) → [02](docs/02-chunking.md) + [03](docs/03-embeddings-and-retrieval.md) → [06](docs/06-rag-principles.md) → [09](docs/09-citations-and-grounding.md) → [04](docs/04-evaluation.md) → [05](docs/05-production.md) + [08](docs/08-anti-patterns.md). Add [07](docs/07-mcp-tools-for-rag.md) for tool-backed retrieval, [12](docs/12-computer-use-tools.md) when agents drive a live UI, and [10](docs/10-multimodal-and-tables.md) when PDFs/tables/images matter. Skim [11](docs/11-faq.md) anytime.

## Examples

Worked sketches and checklists you can copy into a design review:

| Example | Purpose |
| --- | --- |
| [rag-principles-checklist.md](examples/rag-principles-checklist.md) | Design-review checklist |
| [chunking-heuristics.md](examples/chunking-heuristics.md) | Size/overlap heuristics by content type |
| [evaluation-rubric.md](examples/evaluation-rubric.md) | Simple human + auto eval rubric |
| [mcp-tool-schemas.json](examples/mcp-tool-schemas.json) | Illustrative MCP tool definitions |
| [sample-rag-pipeline.md](examples/sample-rag-pipeline.md) | End-to-end sketch: ingest → cite |
| [computer-use-checklist.md](examples/computer-use-checklist.md) | Preflight checklist for UI/browser agents |

## Quick start mindset

1. **Retrieve before generate** — do not invent private facts.
2. **Ground and cite** — answers must point to stable chunk IDs or URLs.
3. **Fail closed** — empty or low-score retrieval → abstain.
4. **Evaluate retrieval separately** from answer fluency.
5. **Prefer hybrid search** when users type IDs, error codes, or rare keywords.

For the full list, see [docs/06-rag-principles.md](docs/06-rag-principles.md). For citations and abstention patterns, see [docs/09-citations-and-grounding.md](docs/09-citations-and-grounding.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to propose improvements. Doc gaps welcome via the [doc improvement](.github/ISSUE_TEMPLATE/doc-improvement.yml) issue template; PRs can use [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md).

## Code of conduct

Participation is governed by the [Contributor Covenant](CODE_OF_CONDUCT.md). Report concerns by opening an issue.

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 grigortodorov.
