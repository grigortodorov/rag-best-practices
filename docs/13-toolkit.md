# 13 — Usable toolkit (`ragpractices`)

A small, stdlib-first Python package that ships with this repo. It does **not** call remote APIs and does not require API keys. Use it to practice chunking, score answers with a simple rubric, and print a design-review checklist.

Related: [02 — Chunking](02-chunking.md) · [04 — Evaluation](04-evaluation.md) · [06 — RAG principles](06-rag-principles.md) · [examples/evaluation-rubric.md](../examples/evaluation-rubric.md)

## Install

From the repository root (editable):

```bash
pip install -e .
ragpractices --help
```

Optional dev extra for pytest:

```bash
pip install -e ".[dev]"
```

Requires Python 3.10+.

## Library API

Import name: `ragpractices`.

```python
from ragpractices import (
    __version__,
    chunk_text,
    chunk_by_headings,
    score_answer,
    format_scorecard,
    get_checklist,
    DIMENSIONS,
)
```

### `chunk_text(text, chunk_size=800, overlap=100) -> list[str]`

Fixed-size character windows with overlap. Empty / whitespace-only input returns `[]`. Raises `ValueError` if `chunk_size <= 0` or if overlap is not in `[0, chunk_size)`.

### `chunk_by_headings(markdown, max_chars=1200) -> list[dict]`

Splits on ATX Markdown headings (`#` … `######`). Each item is `{"text": str, "heading": str}`. A preamble before the first heading uses `heading=""`. Oversized sections are further split with `chunk_text`.

### `score_answer(scores: dict[str, int]) -> dict`

Dimensions (each `0` / `1` / `2`):

| Key | Meaning (spirit of the eval rubric) |
| --- | --- |
| `groundedness` | Claims supported by retrieved context |
| `relevance` | Answer addresses the question |
| `completeness` | Covers the asked point given available context |
| `citation_quality` | Citations present, real, and claim-aligned |

Returns `scores`, `total`, `max` (8), `passed`, and `gate_failures`. **Pass gate:** `groundedness >= 1` (fail closed on fully unsupported answers). Missing/unknown dimensions or out-of-range values raise `ValueError`.

### `format_scorecard(result) -> str`

Plain-text scorecard for humans or logs.

### `get_checklist() -> str`

Short embedded principles checklist (full checklist lives in `examples/rag-principles-checklist.md`).

## CLI

Entry point: `ragpractices`.

### Chunk a file to JSON

```bash
ragpractices chunk examples/sample.txt --chunk-size 120 --overlap 20
ragpractices chunk examples/sample.txt --by-headings --max-chars 200
```

### Score an answer

```bash
ragpractices score --scores groundedness=2,relevance=2,completeness=1,citation_quality=2
```

Omit `--scores` to enter values interactively. Exit code `0` on PASS, `1` on FAIL (gate), `2` on usage/IO errors.

### Print checklist

```bash
ragpractices checklist
```

## Tests

No runtime test dependency. From the repo root:

```bash
python -m unittest discover -s tests -v
```

With the optional `dev` extra:

```bash
pytest -q
```

## Scope and honesty

This toolkit is intentionally small: character/heading chunking and a four-dimension scorecard. It is **not** a retrieval engine, embedder, or benchmark suite. Do not treat demo scores as product metrics; wire your own gold set and retrieval metrics as described in [04 — Evaluation](04-evaluation.md).

## Next

- [examples/sample.txt](../examples/sample.txt) — tiny fixture for the chunk CLI
- [examples/evaluation-rubric.md](../examples/evaluation-rubric.md) — fuller human + auto rubric
- [examples/rag-principles-checklist.md](../examples/rag-principles-checklist.md) — full design-review checklist
