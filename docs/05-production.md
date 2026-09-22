# 05 — Production: Caching, Latency, Cost, Observability, Security

## Caching

- **Embedding cache:** cache vectors for unchanged chunk text + model version
- **Retrieval cache:** cache top-k for identical normalized queries (short TTL if corpus updates often)
- **Answer cache:** only for deterministic, non-personalized, non-sensitive queries

Invalidate on document version bumps.

## Latency budget

Break p95 into: query rewrite, embed query, ANN + sparse, rerank, LLM generate.

Levers:

- Smaller / quantized embedders
- Lower `top_k` into the reranker
- Parallel sparse + dense
- Streaming tokens to the user while sources finalize

## Cost control

- Don't send 20 long chunks when 4 suffice after rerank
- Tier models: cheap draft vs expensive final only when needed
- Batch ingest embeddings
- Cap max context tokens per request

## Observability

Log (with retention and access controls):

- Query id, tenant, latency breakdown
- Retrieved `chunk_id`s and scores
- Model / prompt / index versions
- Empty retrieval and low-score rates
- User feedback linkage

An **audit trail of retrieved context** is essential for debugging and compliance reviews.

## Security and privacy

### PII in indexes

- Minimize PII at ingest; redact or tokenize when possible
- Separate indexes or hard filters per tenant / ACL
- Encrypt at rest; restrict who can run raw similarity search
- Remember: embeddings can still leak signal—treat vector stores as sensitive

### Prompt injection via documents

Retrieved text may contain instructions ("ignore previous..."). Mitigations:

- Delimit context clearly; instruct the model to treat context as untrusted data
- Prefer structured citations over free-form tool execution from chunk text
- Sanitize or refuse risky tool calls suggested only by retrieved content

### Secrets

Never embed API keys or credentials into tool arguments, logs, or chunk text. Use allowlisted tools and server-side credentials.

## Reliability patterns

- **Fail closed** on empty or below-threshold retrieval: abstain rather than hallucinate
- Timeouts and fallbacks (keyword-only, or "search unavailable")
- Canary new indexes; keep rollback to prior index version

## Next

- [06 — RAG principles](06-rag-principles.md)
- [07 — MCP tools for RAG](07-mcp-tools-for-rag.md)
- [08 — Anti-patterns](08-anti-patterns.md)
