# Chunking Heuristics by Content Type

Concrete **starting points** for chunk size and overlap. Tune with retrieval eval ([docs/04-evaluation.md](../docs/04-evaluation.md)); do not treat these as universal laws.

Related: [docs/02-chunking.md](../docs/02-chunking.md) · [docs/10-multimodal-and-tables.md](../docs/10-multimodal-and-tables.md)

## How to read this table

- **Size** is approximate token counts for the embedding/generator tokenizer you actually use
- **Overlap** is a fraction of chunk size (or tokens); prefer structure boundaries over large blind overlap
- Always store stable `chunk_id`, section path, and source metadata

## Heuristics matrix

| Content type | Primary split | Target size | Overlap | Notes |
| --- | --- | --- | --- | --- |
| Policy / wiki prose | Headings → paragraphs | 256–512 tokens | 10–15% | Cap long sections; keep definition + following rule together when possible |
| FAQ / Q&A | One Q+A pair | Whole pair (usually < 300 tokens) | 0–1 sentence | Do not split question from answer |
| Runbooks / how-tos | Numbered steps / H2–H3 | 200–400 tokens | 10% | Keep a step with its prerequisites and expected result |
| API reference | Endpoint or method | Per operation + params | Small / none | Include method, path, and auth notes in the same chunk when feasible |
| Code | Function / class | ≤ ~500–800 tokens | None across functions | Keep signature + docstring + body together; fall back to logical blocks |
| Tables (text-extractable) | Row or row-group | 1–5 rows + header | Header repeated | Never split mid-row; store `table_id` |
| Large tables | Row groups or dual index | Row chunks + optional summary chunk | Header repeated | Consider tool/SQL for exact cell lookup |
| PDFs (digital text) | Layout-aware sections | Same as prose after cleanup | 10–15% | Strip headers/footers first ([docs/10](../docs/10-multimodal-and-tables.md)) |
| Scanned PDFs | OCR → same as PDF | Same as prose | 10–15% | Gate on OCR confidence; spot-check tables |
| Slide decks | Per slide (+ notes) | 1 slide | Title repeated | Title + body + speaker notes; avoid merging unrelated slides |
| Chat / ticket threads | Message groups or turn windows | 300–600 tokens | 1–2 messages | Preserve author + timestamp metadata |
| Release notes | Version section | Per version or subsection | Small | Keep version id in every chunk metadata |
| Diagrams / figures | Caption (+ optional description) | Caption-sized | None | Cite `figure_id` / page; do not invent details from weak captions |

## Overlap rules of thumb

| Situation | Prefer |
| --- | --- |
| Clean Markdown with headings | Structure cuts; overlap ≤ 10% |
| Plain prose without headings | 10–20% overlap or semantic splits |
| Near-duplicate hits in retrieval | Reduce overlap; dedupe before prompting |
| Boundary misses on eval (“answer split across chunks”) | Slightly more overlap **or** hierarchical parent expansion |

## Anti-heuristics (avoid)

- One vector for a 50-page manual
- Same 512-token splitter for FAQs, tables, and code
- 50%+ overlap “just to be safe” (hurts citations and inflates index)
- Chunking before fixing PDF/OCR extraction noise

## Quick validation loop

1. Pick 20 real user questions for this content type
2. Note where the answer lives (section, table row, function)
3. Measure Recall@k for your current chunker
4. Adjust size/boundaries only when failures cluster on a pattern
5. Re-check citation readability in the UI

## Next

- [docs/02-chunking.md](../docs/02-chunking.md)
- [docs/10-multimodal-and-tables.md](../docs/10-multimodal-and-tables.md)
- [sample-rag-pipeline.md](sample-rag-pipeline.md)
