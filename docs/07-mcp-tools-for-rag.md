# 07 — MCP Tools for RAG

[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) lets an assistant call **tools** exposed by servers (search, fetch document, list collections) with typed inputs/outputs. In a RAG stack, MCP tools are a clean way to provide **tool-backed retrieval** instead of—or in addition to—a pure embedded vector store inside the app process.

## Tool-backed retrieval vs pure vector store

| Approach | Strengths | Watch-outs |
| --- | --- | --- |
| Pure vector store in-app | Low latency, simple deploy | ACL and multi-corpus logic live in your service |
| MCP search/fetch tools | Clear boundaries, reusable across clients, easy to swap backends | Extra hop; must harden tool auth and allowlists |
| Hybrid | Embeddings for recall + tools for exact get-by-id / live systems | Need routing rules so the model does not skip retrieval |

Use tools when the model must **fetch by id**, list collections, or hit systems that are not fully embedded (issue trackers, live config, paginated APIs).

## Example tool shapes

Typical docs-RAG assistant tools:

1. **`search_docs`** — query + optional collection/filters → ranked hits with `document_id`, snippet, score
2. **`get_document`** — `document_id` (and optional section) → full text or chunk payload
3. **`list_collections`** — enumerates corpora the caller is allowed to see

See concrete JSON schemas in [examples/mcp-tool-schemas.json](../examples/mcp-tool-schemas.json).

### Example call sequence

```text
list_collections()
  → [{ name: "policies" }, { name: "runbooks" }, ...]

search_docs({
  query: "refund window digital goods",
  collection: "policies",
  top_k: 8
})
  → hits: [{ chunk_id: "docs/refunds.md:chunk-12", score: 0.82, ... }, ...]

get_document({
  document_id: "docs/refunds.md",
  chunk_id: "docs/refunds.md:chunk-12"
})
  → { text: "Customers may request a refund within 30 days...", ... }

→ Generate grounded answer with citations
→ If no hits: abstain (fail closed)
```

## When to use tools vs embeddings

- **Embeddings / hybrid index:** open-ended natural language questions over a corpus
- **`get_document`:** user (or prior hit) already has an id; avoid re-search
- **`list_collections`:** orientation and routing ("which knowledge bases exist?")
- **Live tools (tickets, CRM):** facts that must be current and not stale in an index

A strong pattern: hybrid `search_docs` for candidates, then `get_document` to expand the top citation targets.

## Agent routing rules (recommended)

1. For factual corpus questions → **must** call `search_docs` before answering
2. After search, optionally `get_document` for the top 1–3 ids
3. Never invent `document_id` values; only use ids returned by tools
4. On empty hits → abstain; do not fall back to parametric "memory" for private facts

## Security

- **Allowlist tools** the model may call; do not expose shell or arbitrary HTTP
- **Authorize in the tool server** using the end-user identity—never trust the model to pass "I am admin"
- **No secret leakage in tool args or returns** — API keys stay on the server; redact secrets from document payloads when possible
- **Validate arguments** (max query length, allowed `collection` enum)
- Treat retrieved document text as **untrusted** for further tool use (prompt injection)
- Cap `top_k` and response payload size to limit data exfiltration via tool returns

## Minimal agent flow

```text
User question
  → search_docs(query, collection?)
  → optional get_document(id) for top hits
  → generate grounded answer with citations
  → if no hits: abstain (fail closed)
```

## Next

- [examples/mcp-tool-schemas.json](../examples/mcp-tool-schemas.json)
- [examples/sample-rag-pipeline.md](../examples/sample-rag-pipeline.md)
- [05 — Production security notes](05-production.md)
- [08 — Anti-patterns](08-anti-patterns.md)
