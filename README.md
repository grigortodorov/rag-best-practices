# RAG Best Practices

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/grigortodorov/rag-best-practices/actions/workflows/ci.yml/badge.svg)](https://github.com/grigortodorov/rag-best-practices/actions/workflows/ci.yml)

**Practical, educational guidance for building Retrieval-Augmented Generation (RAG) systems that stay grounded, measurable, and production-safe.**

This repo collects clear principles, tradeoffs, and patterns—chunking, hybrid retrieval, evaluation, citations, multimodal/PDF pitfalls, MCP tool-backed search, computer-use agents alongside RAG, and common anti-patterns. Content is honest and hands-on: **no fabricated metrics, stars, downloads, dependents, or vendor eligibility claims**.

Use it as a design-review companion, an onboarding reading path, or a checklist source when shipping RAG features.

## Table of contents

1. [Who this is for](#who-this-is-for)
2. [Documentation](#documentation)
3. [Usable toolkit](#usable-toolkit)
4. [Examples](#examples)
5. [Quick start mindset](#quick-start-mindset)
6. [Before you ship RAG](#before-you-ship-rag)
7. [Contributing](#contributing)
8. [Code of conduct](#code-of-conduct)
9. [License](#license)

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
| [13 — Toolkit](docs/13-toolkit.md) | Installable `ragpractices` package (ingest / html / chunk / hybrid / rewrite / rerank / pack / ground / cite / eval / compare / prompt / filter / decide / pipeline / quality / demo / score / checklist) |

**Suggested path:** [01](docs/01-overview.md) → [02](docs/02-chunking.md) + [03](docs/03-embeddings-and-retrieval.md) → [06](docs/06-rag-principles.md) → [09](docs/09-citations-and-grounding.md) → [04](docs/04-evaluation.md) → [05](docs/05-production.md) + [08](docs/08-anti-patterns.md). Add [07](docs/07-mcp-tools-for-rag.md) for tool-backed retrieval, [12](docs/12-computer-use-tools.md) when agents drive a live UI, and [10](docs/10-multimodal-and-tables.md) when PDFs/tables/images matter. Skim [11](docs/11-faq.md) anytime. For the installable helpers, see [13](docs/13-toolkit.md).

## Usable toolkit

Installable helpers (`ragpractices`) for document ingest (incl. HTML + content hashing), chunking demos, hybrid search, query rewrite / multi-query, deterministic rerank / MMR, context packing, heuristic groundedness checks, citation formatting, offline retrieval eval (hit@k / MRR) with CI gates, strategy compare, grounded prompt templates, metadata/ACL filters, fail-closed abstain/clarify, configurable pipelines with traces, chunk quality / near-dedupe, a 0–2 answer scorecard, and a short principles checklist. Stdlib-only runtime; no API keys. Package name: `ragpractices` (v0.7.0+). CI runs unit tests plus a retrieval hit-rate gate on push/PR to `main`.

```bash
pip install -e .
ragpractices --help
ragpractices ingest examples/ingest-sample --out /tmp/corpus.jsonl
ragpractices chunk examples/sample.txt --by-headings
ragpractices hybrid "refund shipping" --docs examples/hybrid-docs.txt --fusion rrf --top 3
ragpractices rewrite "refund ship" --multi
ragpractices rerank "refund" --docs examples/hybrid-docs.txt --top 3
ragpractices cite --answer "Refunds are within 30 days [1]." --sources examples/hybrid-docs.txt
ragpractices pack --docs examples/hybrid-docs.txt --max-tokens 40
ragpractices ground --answer "Refunds are within 30 days." --sources examples/hybrid-docs.txt
ragpractices demo --query "refund shipping"
ragpractices eval --golden examples/golden-retrieval.jsonl --docs examples/hybrid-docs.txt --k 3 --min-hit-rate 0.6
ragpractices compare --golden examples/golden-retrieval.jsonl --docs examples/hybrid-docs.txt --k 3
ragpractices prompt --question "What is the refund window?" --docs examples/hybrid-docs.txt --style cite
ragpractices filter --docs examples/acl-docs.jsonl --tenant acme --roles public --tags refund
ragpractices html examples/ingest-sample/faq.html --hash-only
ragpractices decide --top-score 0.05 --groundedness 0.2
ragpractices pipeline --config examples/pipeline.json --query "refund shipping"
ragpractices quality --docs examples/hybrid-docs.txt
ragpractices dedupe --docs examples/hybrid-docs.txt --threshold 0.9
ragpractices score --scores groundedness=2,relevance=2,completeness=1,citation_quality=2
```

Details: [docs/13-toolkit.md](docs/13-toolkit.md).

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
| [sample.txt](examples/sample.txt) | Tiny text fixture for the chunk CLI |
| [hybrid-docs.txt](examples/hybrid-docs.txt) | Tiny multi-doc fixture for the hybrid CLI |
| [ingest-sample/](examples/ingest-sample/) | Tiny multi-file fixture for the ingest CLI |
| [e2e_demo.py](examples/e2e_demo.py) | Runnable end-to-end pipeline (rewrite → ground) |

## Quick start mindset

1. **Retrieve before generate** — do not invent private facts.
2. **Ground and cite** — answers must point to stable chunk IDs or URLs.
3. **Fail closed** — empty or low-score retrieval → abstain.
4. **Evaluate retrieval separately** from answer fluency.
5. **Prefer hybrid search** when users type IDs, error codes, or rare keywords.

For the full list, see [docs/06-rag-principles.md](docs/06-rag-principles.md). For citations and abstention patterns, see [docs/09-citations-and-grounding.md](docs/09-citations-and-grounding.md).


## Before you ship RAG

Short scorecard (also see [examples/rag-principles-checklist.md](examples/rag-principles-checklist.md) and `ragpractices checklist`):

1. **Golden retrieval set** — offline hit@k / MRR on labeled queries (`ragpractices eval`).
2. **Fail closed** — empty or low-score retrieval abstains; weak groundedness clarifies (`ragpractices decide`).
3. **Citations required** — answers point at stable chunk/doc ids, not free-form prose.
4. **Chunk quality** — length stats and near-dupes reviewed (`ragpractices quality` / `dedupe`).
5. **Hybrid for IDs/keywords** — keyword + dense (or RRF) when users type codes, SKUs, or rare terms.
6. **Token-budget packing** — context fits the model window without silent truncation surprises.
7. **Traces in staging** — pipeline stage timings/summaries available for debugging (`ragpractices pipeline`).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for toolkit release notes (`ragpractices` 0.7.0+).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to propose improvements. Doc gaps welcome via the [doc improvement](.github/ISSUE_TEMPLATE/doc-improvement.yml) issue template; PRs can use [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md).

## Code of conduct

Participation is governed by the [Contributor Covenant](CODE_OF_CONDUCT.md). Report concerns by opening an issue.

## License

Released under the [MIT License](LICENSE). Copyright (c) 2026 grigortodorov.
