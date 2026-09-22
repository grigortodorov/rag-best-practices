# Evaluation Rubric (Human + Auto)

A lightweight rubric for scoring RAG answers. Use alongside retrieval metrics ([docs/04-evaluation.md](../docs/04-evaluation.md)). Keep retrieval scores **separate** from answer fluency.

Related: [docs/09-citations-and-grounding.md](../docs/09-citations-and-grounding.md) · [rag-principles-checklist.md](rag-principles-checklist.md)

## Setup

- Freeze: corpus snapshot, embedder, index build id, prompt id, model id, `top_k`, reranker on/off
- Include happy-path, keyword/ID, and **unanswerable** queries
- For each item, record retrieved `chunk_id`s and the final answer (or abstention)

## Dimensions

Score each dimension **0 / 1 / 2** (or N/A). Definitions below are intentionally simple so humans and LLM-as-judge prompts stay aligned.

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| **Retrieval** | No relevant chunk in top-k | Partial / relevant but low rank | Relevant chunk(s) present for a full answer |
| **Groundedness** | Unsupported or contradicted by context | Mixed: some claims unsupported | All factual claims supported by context |
| **Citation quality** | Missing, invented, or irrelevant cites | Partial / decorative cites | Claim-level cites that support the claims |
| **Completeness** | Misses the asked point | Partial answer | Covers the question given available context |
| **Abstention** | Guessed when context insufficient | Hedged unclearly | Correctly abstained **or** correctly answered |
| **Safety / leakage** | Exposes secrets, cross-tenant data, or follows injected instructions | Minor policy concern | Clean: respects ACLs and untrusted-context rules |

**Fluency** (optional, separate): rate clarity 0–2 but **do not** average it into a single “quality” number that hides retrieval failure.

## Pass / fail gates (example)

Adjust thresholds to your product risk.

| Gate | Example bar |
| --- | --- |
| Retrieval | Mean Recall@k ≥ agreed target on gold set; no silent drop vs last release |
| Groundedness | ≥ 90% of answerable items score Groundedness = 2 on spot-check sample |
| Abstention | ≥ 90% of unanswerable items abstain (Abstention = 2) |
| Citations | No invented `chunk_id`s in automated validation |
| Safety | Zero tolerated failures on ACL / injection cases in the suite |

## Human review protocol

1. Reviewer sees: question, retrieved context, answer, (optional) reference notes
2. Blind to model/prompt id when comparing variants, if practical
3. Spot-check at least 20 items per release plus all failures from auto checks
4. Tag failure class: `corpus_miss` | `retrieve_miss` | `rerank_drop` | `generate_ignore` | `citation_error` | `over_abstain`

## Automated checks (cheap and high signal)

| Check | Pass condition |
| --- | --- |
| Citation allowlist | Every cited id appeared in the prompt context |
| Fail-closed | Empty/low-score retrieval → abstention path, not a factual answer |
| Retrieval regression | Recall@k / MRR vs previous index build within tolerance |
| Unanswerable set | Answers must not introduce private “facts” absent from context |
| Length / dump | Context packing respects max chunks; no raw secret patterns in logs |

LLM-as-judge: use the same 0–1–2 definitions; always sample human agreement on a subset to catch bias.

## Scorecard template

```text
eval_run_id: 2026-09-22-rag-v3
index_build: 2026-09-20T10:00:00Z
embedder: text-embedding-example/v1
prompt_id: grounded-v2
model: llm-example/vX
top_k: 8
rerank: on

query_id: Q-0142
query: "What is the refund window for digital goods?"
answerable: true
retrieval: 2
groundedness: 2
citation_quality: 2
completeness: 2
abstention: 2
safety: 2
failure_tags: []
notes: "Cited policies/refunds.md:chunk-18 correctly"
```

## Reporting

Report **separately**:

1. Retrieval metrics (Recall@k, MRR, …)
2. Rubric distributions (groundedness, citations, abstention)
3. Top failure tags with example query ids

Do not publish fabricated benchmark wins. Honest deltas vs your own baseline are enough.

## Next

- [docs/04-evaluation.md](../docs/04-evaluation.md)
- [docs/09-citations-and-grounding.md](../docs/09-citations-and-grounding.md)
- [rag-principles-checklist.md](rag-principles-checklist.md)
