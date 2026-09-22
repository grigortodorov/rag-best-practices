"""Simple text and Markdown chunking helpers (stdlib only)."""

from __future__ import annotations

import re
from typing import Any


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split ``text`` into overlapping character windows.

    Args:
        text: Source text (any plain string).
        chunk_size: Maximum characters per chunk (must be > 0).
        overlap: Characters shared between consecutive chunks
            (``0 <= overlap < chunk_size``).

    Returns:
        Non-empty chunks in document order. Empty / whitespace-only
        input yields an empty list.

    Notes:
        Prefer structure-aware splitting (:func:`chunk_by_headings`) when
        the source has reliable Markdown headings. Overlap reduces
        boundary misses at the cost of duplicated storage.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")

    if not text or not text.strip():
        return []

    step = chunk_size - overlap
    chunks: list[str] = []
    start = 0
    length = len(text)

    while start < length:
        end = min(start + chunk_size, length)
        piece = text[start:end]
        if piece.strip():
            chunks.append(piece)
        if end >= length:
            break
        start += step

    return chunks


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def chunk_by_headings(markdown: str, max_chars: int = 1200) -> list[dict[str, Any]]:
    """Split Markdown into sections by ATX headings, then by size.

    Each result dict has:

    - ``text``: section body (heading line included when present)
    - ``heading``: heading title without ``#`` markers, or ``""`` for
      a leading preamble with no heading

    Long sections are further split with :func:`chunk_text` using
    ``max_chars`` and a modest overlap (10% of ``max_chars``, capped).
    Sub-chunks keep the same ``heading``.

    Args:
        markdown: Markdown source.
        max_chars: Soft max characters per returned chunk (> 0).

    Returns:
        List of ``{"text": str, "heading": str}`` dicts.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")

    if not markdown or not markdown.strip():
        return []

    matches = list(_HEADING_RE.finditer(markdown))
    sections: list[tuple[str, str]] = []  # (heading, body including heading line)

    if not matches:
        sections.append(("", markdown.strip()))
    else:
        # Preamble before first heading
        first = matches[0]
        preamble = markdown[: first.start()].strip()
        if preamble:
            sections.append(("", preamble))

        for i, match in enumerate(matches):
            title = match.group(2).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
            body = markdown[start:end].strip()
            if body:
                sections.append((title, body))

    overlap = min(max(max_chars // 10, 0), max_chars - 1) if max_chars > 1 else 0
    results: list[dict[str, Any]] = []

    for heading, body in sections:
        if len(body) <= max_chars:
            results.append({"text": body, "heading": heading})
            continue
        for piece in chunk_text(body, chunk_size=max_chars, overlap=overlap):
            results.append({"text": piece, "heading": heading})

    return results
