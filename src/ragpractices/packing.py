"""Context packing helpers for token-budgeted RAG prompts (stdlib only).

Token estimates use a simple ~4 characters per token heuristic. This is an
educational approximation for packing demos—not a real tokenizer (tiktoken,
SentencePiece, etc.). Production systems should use the model tokenizer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Heuristic: ~4 characters ≈ 1 token (common rule of thumb for English prose).
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Estimate token count as ``ceil(len(text) / 4)`` (~4 chars/token).

    Empty / whitespace-only text returns ``0``. This is a documented heuristic,
    not a real tokenizer.
    """
    if not text or not text.strip():
        return 0
    n = len(text)
    return (n + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Hard-cap ``text`` to roughly ``max_tokens`` using the chars/token heuristic.

    Truncates at a character boundary (``max_tokens * 4``). Raises ``ValueError``
    if ``max_tokens < 0``. ``max_tokens == 0`` returns ``""``.
    """
    if max_tokens < 0:
        raise ValueError("max_tokens must be >= 0")
    if max_tokens == 0:
        return ""
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _normalize_docs(
    docs: list[str] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize to dicts with ``text``, optional ``id`` / ``score``."""
    out: list[dict[str, Any]] = []
    for i, item in enumerate(docs):
        if isinstance(item, str):
            out.append({"text": item, "id": i})
        elif isinstance(item, dict):
            if "text" not in item and "document" not in item:
                raise ValueError(
                    f"doc at index {i} needs a 'text' (or 'document') field"
                )
            row = dict(item)
            if "text" not in row:
                row["text"] = str(row.get("document") or "")
            if "id" not in row:
                row["id"] = i
            out.append(row)
        else:
            raise TypeError(f"doc at index {i} must be str or dict, got {type(item)}")
    return out


@dataclass
class PackResult:
    """Result of packing documents into a token budget."""

    packed_text: str
    included: list[Any] = field(default_factory=list)
    omitted: list[Any] = field(default_factory=list)
    estimated_tokens: int = 0
    max_tokens: int = 0


def pack_context(
    docs: list[str] | list[dict[str, Any]],
    *,
    max_tokens: int,
    separator: str = "\n\n---\n\n",
    preserve_order: bool = True,
    truncate: bool = False,
) -> PackResult:
    """Greedily pack documents under a token budget.

    Accepts plain strings or dicts with at least ``text`` (optional ``id``,
    ``score``). Documents are considered in input order when
    ``preserve_order=True``; otherwise sorted by ``score`` descending (missing
    scores treated as ``0.0``).

    Oversized single docs are skipped unless ``truncate=True``, in which case
    the first candidate that does not fully fit may be truncated to the
    remaining budget (via :func:`truncate_to_tokens`), and packing stops.

    Args:
        docs: Corpus strings or dicts.
        max_tokens: Soft budget (must be >= 0).
        separator: Joined between included texts.
        preserve_order: Keep input order vs score-sorted.
        truncate: Allow truncating one final partial doc.

    Returns:
        :class:`PackResult` with packed text, included/omitted ids (or indices),
        and estimated token usage of the packed string.
    """
    if max_tokens < 0:
        raise ValueError("max_tokens must be >= 0")

    normalized = _normalize_docs(docs)
    if not normalized:
        return PackResult(
            packed_text="",
            included=[],
            omitted=[],
            estimated_tokens=0,
            max_tokens=max_tokens,
        )

    order = list(range(len(normalized)))
    if not preserve_order:
        order.sort(
            key=lambda i: (-float(normalized[i].get("score") or 0.0), i),
        )

    sep_tokens = estimate_tokens(separator) if separator else 0
    included_texts: list[str] = []
    included_ids: list[Any] = []
    omitted_ids: list[Any] = []
    used = 0
    stopped = False

    for idx in order:
        if stopped:
            omitted_ids.append(normalized[idx].get("id", idx))
            continue

        doc = normalized[idx]
        text = str(doc.get("text") or "")
        doc_id = doc.get("id", idx)
        doc_tokens = estimate_tokens(text)
        extra_sep = sep_tokens if included_texts else 0
        needed = doc_tokens + extra_sep

        if used + needed <= max_tokens:
            included_texts.append(text)
            included_ids.append(doc_id)
            used += needed
            continue

        remaining = max_tokens - used - extra_sep
        if truncate and remaining > 0 and text.strip():
            truncated = truncate_to_tokens(text, remaining)
            if truncated:
                included_texts.append(truncated)
                included_ids.append(doc_id)
                used += extra_sep + estimate_tokens(truncated)
            else:
                omitted_ids.append(doc_id)
            stopped = True
        else:
            # Skip oversized single doc; keep trying later docs.
            omitted_ids.append(doc_id)

    packed = separator.join(included_texts)
    return PackResult(
        packed_text=packed,
        included=included_ids,
        omitted=omitted_ids,
        estimated_tokens=estimate_tokens(packed),
        max_tokens=max_tokens,
    )
