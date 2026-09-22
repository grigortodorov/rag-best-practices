# 04 — Evaluation: Groundedness, Retrieval Metrics, Offline vs Online

Evaluate **retrieval** and **generation** separately. A fluent wrong answer can hide a bad retriever; a good retriever can be wasted by a weak prompt.

## Retrieval metrics (offline)

Build a labeled set: query → relevant `chunk_id`s (or document ids).

| Metric | Meaning |
| --- | --- |
| Recall@k | Fraction of relevant items found in top-k |
| Precision@k | Fraction of top-k that are relevant |
| MRR | How high the first relevant hit ranks |
| nDCG@k | Rank-aware quality with graded relevance |

Start with **Recall@k** at the k you feed the generator (or pre-rerank k). If relevant chunks never enter the prompt, generation cannot fix that.

## Generation / answer quality

- **Groundedness / faithfulness:** Claims in the answer are supported by retrieved context
- **Correctness:** Matches reference answers or human judgment where labeled
- **Citation quality:** Cited chunks actually support the cited claims
- **Abstention:** Model says "I don't know" when context is insufficient

Use LLM-as-judge carefully: fix rubrics, sample human review, and watch position bias.

## Offline vs online

| | Offline | Online |
| --- | --- | --- |
| Data | Curated eval sets | Live traffic, feedback |
| Strengths | Repeatable, safe to iterate | Catches real query mix |
| Risks | Distribution shift | Noise, sparse labels |

Run offline gates in CI for index/prompt changes. Complement with online signals: thumbs, citation clicks, escalation rate, empty-retrieval rate.

## Failure analysis checklist

1. Was the right chunk in the corpus?
2. Was it retrieved at rank ≤ k?
3. Did reranking drop it?
4. Did the prompt instruct grounding and abstention?
5. Did the model ignore context anyway?

## Minimal eval harness

- 50–200 gold questions spanning happy path, keyword/ID queries, and unanswerable cases
- Fixed corpus snapshot and model versions in the report
- Track retrieval and groundedness as separate scores
- Record: embedder version, index build id, prompt template id, `top_k`, reranker on/off

### Example eval row

```text
query_id: Q-0142
query: "What is the refund window for digital goods?"
relevant_chunk_ids: [policies/refunds.md:chunk-12, policies/refunds.md:chunk-18]
retrieved@8: [..., policies/refunds.md:chunk-12, ...]
recall@8: 1.0
answer_grounded: true
cited: [policies/refunds.md:chunk-12]
```

## Next

- [05 — Production](05-production.md)
- [08 — Anti-patterns](08-anti-patterns.md)
