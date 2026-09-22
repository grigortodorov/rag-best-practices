# 08 — RAG Anti-Patterns (Common Mistakes)

Patterns that repeatedly cause weak, unsafe, or expensive RAG systems—and what to do instead.

## 1. Generate without retrieving

**Mistake:** Asking the LLM private/policy questions with no retrieval or tool call.  
**Why it hurts:** Confident hallucinations; no citations.  
**Fix:** Enforce retrieve-or-tool-before-answer for corpus facts ([06 — Principles](06-rag-principles.md)).

## 2. Giant chunks or whole-document embeddings

**Mistake:** One vector per 50-page manual.  
**Why it hurts:** Diluted similarity; poor citations; wasted context.  
**Fix:** Structure-aware chunking with a max token cap ([02 — Chunking](02-chunking.md)).

## 3. Dense-only search for ID-heavy corpora

**Mistake:** Skipping BM25/keyword for error codes, SKUs, ticket ids.  
**Why it hurts:** Exact-term misses.  
**Fix:** Hybrid search + eval on keyword queries ([03 — Retrieval](03-embeddings-and-retrieval.md)).

## 4. Stuffing the context window

**Mistake:** Sending every low-score hit until the token limit.  
**Why it hurts:** Noise, cost, distraction, injection surface.  
**Fix:** Rerank, score threshold, dedupe, small top-n.

## 5. No abstention path

**Mistake:** Always producing an answer even when retrieval is empty.  
**Why it hurts:** Silent fabrication.  
**Fix:** Fail closed; return "not found" with suggested refinements.

## 6. Evaluating only answer fluency

**Mistake:** Judging demos by prose quality alone.  
**Why it hurts:** Masks retrieval failures.  
**Fix:** Separate Recall@k / MRR from groundedness ([04 — Evaluation](04-evaluation.md)).

## 7. Ignoring metadata and ACLs

**Mistake:** Global similarity search across tenants.  
**Why it hurts:** Data leaks between customers/teams.  
**Fix:** Hard filters at retrieve time; authorize in the tool server.

## 8. Mixing embedding model versions in one index

**Mistake:** Partial re-embed after a model upgrade.  
**Why it hurts:** Nonsense nearest neighbors.  
**Fix:** Version the index; full rebuild on embedder change.

## 9. Blind trust of retrieved text (prompt injection)

**Mistake:** Letting chunk text drive privileged tool calls.  
**Why it hurts:** Indirect prompt injection.  
**Fix:** Delimit untrusted context; allowlist tools; server-side auth ([05 — Production](05-production.md), [07 — MCP](07-mcp-tools-for-rag.md)).

## 10. No audit trail

**Mistake:** Logging only the final answer string.  
**Why it hurts:** Cannot debug or comply.  
**Fix:** Persist query id → chunk ids/scores → model/prompt/index versions.

## 11. Stale indexes without invalidation

**Mistake:** Docs updated in the CMS but never reindexed.  
**Why it hurts:** Correct retrieval of wrong facts.  
**Fix:** Versioned ingest; TTL or event-driven reindex; show `updated_at` in citations when useful.

## 12. Overlapping chunks without citation hygiene

**Mistake:** Huge overlap producing near-duplicate hits cited as different sources.  
**Why it hurts:** User confusion; inflated "coverage."  
**Fix:** Moderate overlap; dedupe near-duplicates before prompting.

## 13. One-size chunking for all content types

**Mistake:** Same 512-token splitter for FAQs, tables, and code.  
**Why it hurts:** Broken tables; split functions; weak FAQ match.  
**Fix:** Content-type-specific strategies ([02 — Chunking](02-chunking.md), [examples/chunking-heuristics.md](../examples/chunking-heuristics.md), [10 — Multimodal](10-multimodal-and-tables.md)).

## 14. Secrets in examples, logs, or tool args

**Mistake:** Pasting API keys into schemas, notebooks, or MCP arguments.  
**Why it hurts:** Credential leaks.  
**Fix:** Server-side secrets only; redact; keep examples illustrative ([examples/mcp-tool-schemas.json](../examples/mcp-tool-schemas.json)).

## Quick triage

| Symptom | Likely anti-pattern |
| --- | --- |
| Fluent but wrong | 1, 5, 6 |
| Misses exact error codes | 3 |
| "Answer is in the PDF somewhere" | 2, 13 |
| Cross-tenant leakage | 7, 9 |
| Quality cliff after model upgrade | 8 |
| Cannot reproduce a bad answer | 10 |

## Next

- [examples/rag-principles-checklist.md](../examples/rag-principles-checklist.md)
- [examples/sample-rag-pipeline.md](../examples/sample-rag-pipeline.md)
- [09 — Citations and grounding](09-citations-and-grounding.md)
- [10 — Multimodal and tables](10-multimodal-and-tables.md)
- [11 — FAQ](11-faq.md)
