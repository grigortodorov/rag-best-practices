"""Query rewrite stubs for multi-query / expansion demos (stdlib only).

Deterministic heuristics — no LLM calls. Useful for illustrating expand,
clarify, and hyphen/camelCase splitting before retrieval.
"""

from __future__ import annotations

import re
from typing import Any

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?", re.IGNORECASE)
_CAMEL_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\b)|\d+")
_HYPHEN_SPLIT_RE = re.compile(r"[-_/]+")

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "can",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "my",
        "your",
        "with",
        "from",
        "by",
        "as",
        "about",
        "into",
        "how",
        "what",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "why",
    }
)

# Bidirectional-ish synonym expansions for common ops / support vocabulary.
_SYNONYMS: dict[str, tuple[str, ...]] = {
    "refund": ("return", "reimbursement"),
    "return": ("refund",),
    "ship": ("shipping", "delivery"),
    "shipping": ("ship", "delivery"),
    "delivery": ("shipping", "ship"),
    "password": ("auth", "authentication", "login"),
    "auth": ("password", "authentication"),
    "authentication": ("password", "auth"),
    "login": ("password", "auth"),
    "order": ("purchase",),
    "purchase": ("order",),
    "cancel": ("cancellation",),
    "cancellation": ("cancel",),
    "policy": ("policies",),
    "policies": ("policy",),
}

_MODES = frozenset({"expand", "clarify", "hyphenate_split"})


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.casefold())


def _clean_whitespace(text: str) -> str:
    return " ".join(text.split())


def _keywords(tokens: list[str]) -> list[str]:
    """Light stopword trim; preserve order and uniqueness."""
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t in _STOPWORDS:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _expand_tokens(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Return expanded token list (original + synonyms) and notes."""
    notes: list[str] = []
    expanded: list[str] = []
    seen: set[str] = set()
    for t in tokens:
        if t not in seen:
            expanded.append(t)
            seen.add(t)
        syns = _SYNONYMS.get(t)
        if not syns:
            continue
        added = [s for s in syns if s not in seen]
        for s in added:
            expanded.append(s)
            seen.add(s)
        if added:
            notes.append(f"expanded {t!r} -> {', '.join(added)}")
    return expanded, notes


def _split_compound_token(raw: str) -> list[str]:
    """Split one camelCase / hyphenated / underscored token into pieces."""
    parts: list[str] = []
    for piece in _HYPHEN_SPLIT_RE.split(raw):
        piece = piece.strip()
        if not piece:
            continue
        camel_bits = _CAMEL_RE.findall(piece)
        if camel_bits and (
            len(camel_bits) > 1 or (camel_bits[0].casefold() != piece.casefold())
        ):
            parts.extend(b for b in camel_bits if b)
        else:
            parts.append(piece)
    return parts if parts else [raw]


def _hyphenate_split_query(query: str) -> tuple[str, list[str]]:
    """Split camelCase and hyphenated tokens; return rewritten + notes."""
    notes: list[str] = []
    # Keep non-space separators as soft boundaries but also catch CamelCase words.
    chunks = re.findall(r"\S+", query)
    rewritten_parts: list[str] = []
    for chunk in chunks:
        pieces = _split_compound_token(chunk)
        if len(pieces) > 1 and "".join(pieces) != chunk.replace("-", "").replace(
            "_", ""
        ).replace("/", ""):
            # Always note when we actually split into multiple tokens
            notes.append(f"split {chunk!r} -> {' '.join(pieces)}")
        elif len(pieces) > 1:
            notes.append(f"split {chunk!r} -> {' '.join(pieces)}")
        rewritten_parts.extend(pieces)
    rewritten = " ".join(rewritten_parts)
    # Normalize to space-separated alphanumeric-ish tokens for retrieval demos
    tokens = _tokenize(rewritten)
    if tokens:
        rewritten = " ".join(tokens)
    return rewritten, notes


def rewrite_query(query: str, *, mode: str = "expand") -> dict[str, Any]:
    """Rewrite a query with deterministic heuristics.

    Args:
        query: Original user query.
        mode: ``expand``, ``clarify``, or ``hyphenate_split``.

    Returns:
        Dict with keys ``original``, ``rewritten``, ``mode``, ``notes``.
        Expand mode also includes a ``keywords`` list (stopword-trimmed).
    """
    if mode not in _MODES:
        raise ValueError(
            f"mode must be one of {sorted(_MODES)}, got {mode!r}"
        )

    original = query
    cleaned = _clean_whitespace(query)
    tokens = _tokenize(cleaned)
    notes: list[str] = []

    if mode == "expand":
        expanded, expand_notes = _expand_tokens(tokens)
        notes.extend(expand_notes)
        rewritten = " ".join(expanded) if expanded else cleaned
        keywords = _keywords(expanded if expanded else tokens)
        if not expand_notes:
            notes.append("no synonym expansions applied")
        return {
            "original": original,
            "rewritten": rewritten,
            "mode": mode,
            "notes": notes,
            "keywords": keywords,
        }

    if mode == "clarify":
        if len(tokens) < 4:
            hint = "(looking for policy details)"
            rewritten = f"{cleaned} {hint}".strip() if cleaned else hint
            notes.append("short query (<4 tokens); appended context hint")
        else:
            rewritten = cleaned
            notes.append("query long enough; returned cleaned query")
        return {
            "original": original,
            "rewritten": rewritten,
            "mode": mode,
            "notes": notes,
        }

    # hyphenate_split
    rewritten, split_notes = _hyphenate_split_query(cleaned if cleaned else query)
    notes.extend(split_notes)
    if not split_notes:
        notes.append("no camelCase/hyphen splits needed")
    return {
        "original": original,
        "rewritten": rewritten,
        "mode": mode,
        "notes": notes,
    }


def multi_query(query: str) -> list[str]:
    """Return 2–3 variant strings for multi-query retrieval demos.

    Variants (deduplicated, stable order):
    1. cleaned original
    2. expand rewrite
    3. keyword-only join from expand keywords
    """
    cleaned = _clean_whitespace(query)
    expanded = rewrite_query(query, mode="expand")
    variants: list[str] = []

    def _add(s: str) -> None:
        s = _clean_whitespace(s)
        if s and s not in variants:
            variants.append(s)

    _add(cleaned)
    _add(str(expanded["rewritten"]))
    keywords = expanded.get("keywords") or []
    if keywords:
        _add(" ".join(keywords))

    # Ensure at least one variant even for empty/whitespace input.
    if not variants:
        variants.append(cleaned or query)
    return variants[:3]
