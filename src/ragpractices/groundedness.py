"""Heuristic groundedness check stub (stdlib only, no LLM).

Educational overlap metric: measures how many content words from the answer
appear in the union of source texts. This is **not** a production NLI /
entailment judge—use real groundedness evaluators (LLM-as-judge, NLI models,
citation verification) in production.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")

# Light English stopword set for content-word filtering.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "as",
        "by",
        "with",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "we",
        "they",
        "them",
        "their",
        "our",
        "your",
        "my",
        "me",
        "him",
        "her",
        "not",
        "no",
        "yes",
        "do",
        "does",
        "did",
        "have",
        "has",
        "had",
        "will",
        "would",
        "can",
        "could",
        "should",
        "may",
        "might",
        "must",
        "than",
        "then",
        "so",
        "such",
        "into",
        "about",
        "up",
        "out",
        "over",
        "after",
        "before",
        "between",
        "under",
        "again",
        "further",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "any",
        "only",
        "own",
        "same",
        "too",
        "very",
        "just",
        "also",
        "than",
    }
)

_STUB_NOTES = (
    "Heuristic stub: fraction of answer content words found in source texts. "
    "Not a production NLI/entailment judge—use LLM-as-judge or citation "
    "verification for real groundedness evaluation."
)

# Sentences below this content-word overlap ratio are flagged unsupported.
_DEFAULT_SENTENCE_THRESHOLD = 0.35


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.casefold())


def _content_words(text: str) -> list[str]:
    """Lowercase alphanumeric tokens minus a light stopword list."""
    return [t for t in _tokenize(text) if t not in _STOPWORDS and len(t) > 1]


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_RE.split(text.strip()) if p and p.strip()]
    return parts if parts else ([text.strip()] if text.strip() else [])


def _source_text(item: str | dict[str, Any]) -> tuple[Any, str]:
    if isinstance(item, str):
        return None, item
    if isinstance(item, dict):
        sid = item.get("id", item.get("index"))
        text = str(
            item.get("text")
            or item.get("document")
            or item.get("snippet")
            or ""
        )
        return sid, text
    raise TypeError(f"source must be str or dict, got {type(item)}")


@dataclass
class GroundednessReport:
    """Heuristic groundedness report (educational stub)."""

    score: float
    supported_word_ratio: float
    unsupported_sentences: list[str] = field(default_factory=list)
    per_source: list[dict[str, Any]] = field(default_factory=list)
    notes: str = _STUB_NOTES


def check_groundedness(
    answer: str,
    sources: list[str] | list[dict[str, Any]],
    *,
    min_overlap: float = 0.0,
    sentence_threshold: float = _DEFAULT_SENTENCE_THRESHOLD,
) -> GroundednessReport:
    """Measure answer↔source word overlap (heuristic stub, not NLI).

    Tokenizes with lowercase alphanumeric words and a light stopword filter.
    ``supported_word_ratio`` is the fraction of unique answer content words
    that appear in the union of source content words. ``score`` equals that
    ratio (clamped to ``[0, 1]``); callers may treat scores below
    ``min_overlap`` as failing a soft gate (the report still returns the raw
    score).

    Also reports per-source overlap (fraction of answer content words found
    in that source) and unsupported answer sentences (content-word overlap
    with the source union below ``sentence_threshold``).

    Args:
        answer: Model answer text.
        sources: Source strings or dicts with ``text`` / ``document``.
        min_overlap: Soft threshold documented in notes when score is below it.
        sentence_threshold: Per-sentence overlap cutoff for ``unsupported_sentences``.

    Returns:
        :class:`GroundednessReport`.
    """
    if not 0.0 <= min_overlap <= 1.0:
        raise ValueError("min_overlap must be in [0, 1]")
    if not 0.0 <= sentence_threshold <= 1.0:
        raise ValueError("sentence_threshold must be in [0, 1]")

    answer_words = _content_words(answer)
    answer_unique = list(dict.fromkeys(answer_words))

    source_rows: list[tuple[Any, str, set[str]]] = []
    union: set[str] = set()
    for i, src in enumerate(sources):
        sid, text = _source_text(src)
        if sid is None:
            sid = f"doc-{i}"
        words = set(_content_words(text))
        union |= words
        source_rows.append((sid, text, words))

    if not answer_unique:
        ratio = 1.0 if not answer.strip() else 0.0
        per_source = [
            {
                "id": sid,
                "overlap": 0.0,
                "matched_words": 0,
                "answer_content_words": 0,
            }
            for sid, _, _ in source_rows
        ]
        notes = _STUB_NOTES
        if min_overlap > 0 and ratio < min_overlap:
            notes += f" Score {ratio:.3f} is below min_overlap={min_overlap}."
        return GroundednessReport(
            score=ratio,
            supported_word_ratio=ratio,
            unsupported_sentences=[],
            per_source=per_source,
            notes=notes,
        )

    matched = [w for w in answer_unique if w in union]
    ratio = len(matched) / len(answer_unique)
    score = max(0.0, min(1.0, ratio))

    per_source: list[dict[str, Any]] = []
    for sid, _text, words in source_rows:
        hits = [w for w in answer_unique if w in words]
        ov = len(hits) / len(answer_unique)
        per_source.append(
            {
                "id": sid,
                "overlap": round(ov, 4),
                "matched_words": len(hits),
                "answer_content_words": len(answer_unique),
            }
        )

    unsupported: list[str] = []
    for sent in _split_sentences(answer):
        sw = list(dict.fromkeys(_content_words(sent)))
        if not sw:
            continue
        sent_hits = sum(1 for w in sw if w in union)
        sent_ratio = sent_hits / len(sw)
        if sent_ratio < sentence_threshold:
            unsupported.append(sent)

    notes = _STUB_NOTES
    if min_overlap > 0 and score < min_overlap:
        notes += f" Score {score:.3f} is below min_overlap={min_overlap}."

    return GroundednessReport(
        score=score,
        supported_word_ratio=ratio,
        unsupported_sentences=unsupported,
        per_source=per_source,
        notes=notes,
    )
