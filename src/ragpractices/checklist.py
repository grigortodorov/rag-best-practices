"""Short RAG principles checklist for CLI and library use."""

from __future__ import annotations

CHECKLIST_TEXT = """\
RAG principles checklist (short)
================================
Use in design reviews or before shipping a RAG change.
Full version: examples/rag-principles-checklist.md

Retrieval
---------
[ ] Retrieve (or call search tools) before factual generation
[ ] Prefer hybrid search for IDs, codes, and rare keywords
[ ] Document top_k / score thresholds; empty retrieval fails closed
[ ] Tune chunking against real questions
[ ] Apply tenant/ACL/metadata filters at retrieve time
[ ] Deduplicate near-duplicate chunks before packing context

Grounding and citations
-----------------------
[ ] Require answers grounded in provided context
[ ] Define abstain behavior when context is insufficient
[ ] Include stable citations (chunk_id / URL / section)
[ ] Spot-check citations on the eval set
[ ] Treat retrieved text as untrusted (delimit; no privileged tools from chunk text)

Evaluation
----------
[ ] Track retrieval metrics separately from answer fluency
[ ] Include keyword/ID and unanswerable queries in the gold set
[ ] Record index, embedder, chunker, and prompt versions per run
[ ] Tag failures: corpus_miss | retrieve_miss | generate_ignore | citation_error

Production
----------
[ ] Audit trail: query → chunks/scores → model/prompt/index versions
[ ] Enforce ACLs at retrieve time
[ ] Consider PII minimization for the index
[ ] Tool allowlists; no secrets in tool arguments
[ ] Cache invalidation tied to document version bumps
[ ] Latency budget: embed / retrieve / rerank / generate
[ ] Index rollback / canary plan documented
"""


def get_checklist() -> str:
    """Return the embedded short principles checklist."""
    return CHECKLIST_TEXT
