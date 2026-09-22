# 10 — Multimodal and Tables in RAG

Real corpora are not plain Markdown. PDFs, tables, screenshots, and diagrams break naive “split every N tokens” pipelines. This guide covers practical approaches and pitfalls—without claiming a single vendor-specific stack is required.

Related: [02 — Chunking](02-chunking.md), [examples/chunking-heuristics.md](../examples/chunking-heuristics.md).

## Goals

- Preserve **structure** that carries meaning (headers, rows, figure captions)
- Produce chunks that are **retrievable** and **citable**
- Avoid indexing garbage from bad OCR or broken PDF extraction
- Know when to use **text**, **vision**, or **tool-backed** lookup instead of stuffing pixels into embeddings

## PDFs

### Extraction first, clever chunking second

1. Extract text with a PDF library or service
2. Detect layout: columns, headers/footers, page numbers
3. Strip repeated headers/footers and watermark noise
4. Reconstruct reading order (multi-column is a common failure)
5. Then apply structure-aware chunking

**Smell tests for bad extraction:**

- Words glued together or split with random newlines
- Tables turned into a shuffle of cell fragments
- Footers mixed into body paragraphs (“Page 3 of 40 Confidential”)
- Ligatures and hyphenation artifacts (`retriev- al`)

If extraction is poor, **fix ingest** before tuning the embedder. Retrieval cannot recover meaning that never entered the index.

### Scanned PDFs

Scanned pages need OCR. Expect:

- Character confusions (`0/O`, `1/l`, `rn/m`)
- Lost column order
- Missing or garbled tables
- Language/script mismatches if the OCR model is wrong

Mitigations: OCR confidence thresholds, human spot-checks on critical docs, dual-pass OCR for high-value corpora, and storing page images for citation preview even when you index text.

## Tables

Tables are first-class content in policies, pricing, and runbooks.

| Strategy | Idea | Pros | Cons |
| --- | --- | --- | --- |
| Row chunks + repeated header | Each row (or small row group) with column headers prepended | Good for “lookup” questions | Larger index; header duplication |
| Section + table summary | Keep table together under a section; optional LLM/text summary for recall | Preserves relationships | Large tables may exceed chunk caps |
| Dual representation | Index both serialized text and a structured form (CSV/JSON) for tools | Exact get-by-key via tools | More pipeline complexity |
| Image of table + caption | Vision or caption embedding when text extract fails | Last resort for scanned sheets | Weaker citations; harder grounding |

**Serialization tip:** Prefer a predictable text form:

```text
Table: Refund windows by product type
| Product type | Window | Notes |
| Digital goods | 30 days | Unless final sale |
| Hardware | 14 days | Unopened |
```

Or row-oriented chunks:

```text
Refund windows by product type — row: Digital goods | Window: 30 days | Notes: Unless final sale
```

Always store `table_id` / section path in metadata so citations can open the right place.

## Images and diagrams

Common cases: architecture diagrams, UI screenshots, handwritten whiteboard photos, chart images in PDFs.

| Approach | When it helps | Limits |
| --- | --- | --- |
| **Caption / alt text** indexing | Docs already have good captions | Weak if captions are missing |
| **Vision model description at ingest** | Need searchable text from figures | Descriptions can hallucinate; version the describer |
| **Multimodal embeddings** | Query-by-image or mixed text/image search | Ecosystem and eval still maturing; cite carefully |
| **Don’t index the image; link it** | Figure is illustrative only | User must open source for detail |
| **Tool / API for the underlying data** | Chart backs a metrics system | Prefer live data over OCR of a PNG |

**Grounding rule:** If the answer depends on pixels the model “saw” only via a generated caption, treat that as weaker evidence than extracted text—and say so in product UX when stakes are high.

## OCR pitfalls (checklist)

- [ ] Language(s) configured correctly
- [ ] DPI / image quality sufficient for small fonts
- [ ] Reading order verified on multi-column layouts
- [ ] Tables validated on a sample (not only body prose)
- [ ] Hyphenation and line-break joins handled
- [ ] Low-confidence regions flagged or excluded
- [ ] Page numbers / headers stripped before chunking
- [ ] Sample of OCR text reviewed by a human before full reindex

## Structure-aware chunking for mixed docs

Prefer hierarchy over blind windows:

```text
Document
  └─ Section (heading path)
       ├─ Prose paragraphs → token-capped chunks + small overlap
       ├─ Table → row/section strategy + header context
       ├─ Code block → function/class boundaries
       └─ Figure → caption (+ optional description) with page/figure id
```

Practical defaults (starting points—tune with eval):

| Region type | Starting point |
| --- | --- |
| Prose | 256–512 tokens, ~10% overlap, split on headings first |
| Table rows | 1–5 rows + header; avoid splitting mid-row |
| Code | Whole function/class when reasonable; else logical blocks |
| Figure captions | Keep caption with figure id; do not merge unrelated figures |

See [examples/chunking-heuristics.md](../examples/chunking-heuristics.md) for a broader matrix.

## Retrieval and citation tips

- Cite **page + section** (or `figure_id` / `table_id`) for PDFs so users can jump back
- For table answers, prefer quoting the **cell values** with the table citation over vague paraphrase
- Hybrid search still matters: SKUs and error codes often live in tables
- Deduplicate near-identical header-prefixed row chunks before packing context

## When multimodal RAG is the wrong hammer

- The “image” is a screenshot of text you could extract properly—as text
- The user needs a live metric—call an API/tool, do not OCR last quarter’s slide
- The corpus is already clean Markdown—add complexity only when eval shows a gap

## Next

- [02 — Chunking](02-chunking.md)
- [examples/chunking-heuristics.md](../examples/chunking-heuristics.md)
- [03 — Embeddings and retrieval](03-embeddings-and-retrieval.md)
- [09 — Citations and grounding](09-citations-and-grounding.md)
- [08 — Anti-patterns](08-anti-patterns.md)
