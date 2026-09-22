"""Claim-level support + sensitive entity/number faithfulness (stdlib only).

Educational heuristic that complements aggregate groundedness and citation-span
checks. Splits an answer into claims, scores content-word overlap against
sources, and verifies hard entities (numbers, dates, ids) appear in sources.

This is **not** a production NLI / entailment judge—use real claim verification
(LLM-as-judge, NLI models, citation auditors) in production.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Sequence

# Reuse the same sentence / content-word ideas as groundedness (duplicated lightly
# so this module stays readable without relying on private helpers).
_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")

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
    }
)

_STUB_NOTES = (
    "Educational heuristic claim-support check (content-word overlap + "
    "entity/number substring match). Not a production NLI / entailment judge—"
    "use LLM-as-judge or dedicated claim verification for real faithfulness."
)

# Dates: ISO, Month DD, YYYY, and slash forms
_DATE_RE = re.compile(
    r"\b("
    r"\d{4}-\d{2}-\d{2}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*"
    r"\.?\s+\d{1,2},?\s+\d{4}"
    r"|\d{1,2}/\d{1,2}/\d{2,4}"
    r")\b",
    re.IGNORECASE,
)

# IDs: UPPERCASE alnum codes with a digit (len>=4), #digits, or bare >=5 digits
_ID_CODE_RE = re.compile(r"\b(?=[A-Z0-9-]{4,}\b)(?=[A-Z0-9-]*\d)[A-Z][A-Z0-9-]*\b")
_ID_HASH_RE = re.compile(r"#\d{3,}\b")
_ID_LONG_DIGIT_RE = re.compile(r"\b\d{5,}\b")

# Numbers: optional commas, optional decimal, optional trailing %
# (applied after dates/ids so those spans are not double-counted as numbers)
_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9/.-])"
    r"("
    r"\d{1,3}(?:,\d{3})+(?:\.\d+)?%?"  # 1,200 or 1,200.5 or 1,200%
    r"|\d+\.\d+%?"  # 3.14 or 15.5%
    r"|\d+%?"  # 42 or 15%
    r")"
    r"(?![A-Za-z0-9/.-])"
)

# Lone 4-digit years (1900–2099) skipped when extracting bare numbers
_YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")

_MIN_CONTENT_WORDS = 3
_DEFAULT_SUPPORTED = 0.55
_DEFAULT_WEAK = 0.30


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.casefold())


def _content_words(text: str) -> list[str]:
    return [t for t in _tokenize(text) if t not in _STOPWORDS and len(t) > 1]


def _source_text(item: str | dict[str, Any]) -> tuple[str | None, str]:
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
        return (str(sid) if sid is not None else None), text
    raise TypeError(f"source must be str or dict, got {type(item)}")


def split_claims(answer: str) -> list[str]:
    """Split ``answer`` into claim sentences (heuristic).

    Uses sentence-boundary splitting similar to groundedness. Drops empty
    parts and very short fragments with fewer than 3 content words.
    """
    text = (answer or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in _SENTENCE_RE.split(text) if p and p.strip()]
    if not parts:
        parts = [text]
    claims: list[str] = []
    for part in parts:
        cw = _content_words(part)
        if len(cw) < _MIN_CONTENT_WORDS:
            continue
        claims.append(part)
    return claims


def extract_sensitive_tokens(text: str) -> list[tuple[str, str]]:
    """Extract (token, kind) for numbers, dates, and ids from ``text``.

    Kinds are ``\"number\"``, ``\"date\"``, or ``\"id\"``. Dates and ids are
    preferred over overlapping number matches. Lone 4-digit years are skipped
    as bare numbers (dates catch explicit date patterns separately).
    """
    if not text:
        return []

    found: list[tuple[str, str, int, int]] = []  # token, kind, start, end
    occupied: list[tuple[int, int]] = []

    def _overlaps(start: int, end: int) -> bool:
        for a, b in occupied:
            if start < b and end > a:
                return True
        return False

    def _add(token: str, kind: str, start: int, end: int) -> None:
        if _overlaps(start, end):
            return
        occupied.append((start, end))
        found.append((token, kind, start, end))

    for m in _DATE_RE.finditer(text):
        _add(m.group(1), "date", m.start(1), m.end(1))

    for m in _ID_CODE_RE.finditer(text):
        _add(m.group(0), "id", m.start(), m.end())
    for m in _ID_HASH_RE.finditer(text):
        _add(m.group(0), "id", m.start(), m.end())
    for m in _ID_LONG_DIGIT_RE.finditer(text):
        _add(m.group(0), "id", m.start(), m.end())

    for m in _NUMBER_RE.finditer(text):
        raw = m.group(1)
        # Skip lone years; skip if already covered by date/id span
        bare = raw.rstrip("%").replace(",", "")
        if _YEAR_RE.match(bare) and "%" not in raw and "." not in raw:
            continue
        _add(raw, "number", m.start(1), m.end(1))

    # Stable order by appearance
    found.sort(key=lambda x: x[2])
    # Deduplicate identical (token, kind) keeping first occurrence
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for token, kind, _s, _e in found:
        key = (token, kind)
        if key in seen:
            continue
        seen.add(key)
        out.append((token, kind))
    return out


def _normalize_entity(token: str) -> str:
    """Casefold and lightly normalize for substring search in sources."""
    t = token.casefold().strip()
    # Keep commas/% for exact-ish match; also try without thousands commas
    return t


def _entity_in_sources(token: str, source_texts_cf: list[str]) -> bool:
    norm = _normalize_entity(token)
    if not norm:
        return False
    variants = {norm}
    # Also try without thousands separators for numbers like 1,200
    if "," in norm:
        variants.add(norm.replace(",", ""))
    for src in source_texts_cf:
        for v in variants:
            if v in src:
                return True
    return False


def _claim_overlap(
    claim: str,
    union: set[str],
    source_rows: list[tuple[str, set[str]]],
) -> tuple[float, str | None]:
    words = list(dict.fromkeys(_content_words(claim)))
    if not words:
        return 0.0, None
    hits = sum(1 for w in words if w in union)
    ratio = hits / len(words)
    best_id: str | None = None
    best_ov = -1.0
    for sid, swords in source_rows:
        shits = sum(1 for w in words if w in swords)
        ov = shits / len(words)
        if ov > best_ov:
            best_ov = ov
            best_id = sid
    return ratio, best_id


@dataclass
class ClaimResult:
    """One claim scored against sources."""

    text: str
    status: Literal["supported", "weak", "unsupported"]
    overlap: float
    best_source_id: str | None


@dataclass
class EntityHit:
    """One sensitive token checked for presence in sources."""

    token: str
    kind: Literal["number", "date", "id"]
    found_in_sources: bool


@dataclass
class ClaimCheckReport:
    """Aggregate claim-support + entity faithfulness report."""

    claims: list[ClaimResult] = field(default_factory=list)
    entities: list[EntityHit] = field(default_factory=list)
    n_supported: int = 0
    n_weak: int = 0
    n_unsupported: int = 0
    n_missing_entities: int = 0
    decision: Literal["pass", "rewrite", "abstain"] = "abstain"
    reasons: list[str] = field(default_factory=list)
    notes: str = _STUB_NOTES


def check_claims(
    answer: str,
    sources: Sequence[dict[str, Any] | str],
    *,
    supported_threshold: float = _DEFAULT_SUPPORTED,
    weak_threshold: float = _DEFAULT_WEAK,
) -> ClaimCheckReport:
    """Score claim-level support and sensitive-entity faithfulness.

    For each claim (sentence), content-word recall vs the union of source texts
    labels ``supported`` / ``weak`` / ``unsupported``. Sensitive tokens from
    the whole answer (numbers, dates, ids) must appear as substrings in some
    source (casefold). Decision is fail-closed:

    - ``abstain`` — empty answer, any unsupported claim, or any missing entity
    - ``rewrite`` — no hard fails but at least one weak claim
    - ``pass`` — all claims supported (or no claims) and no missing entities

    Args:
        answer: Model answer text.
        sources: Source strings or dicts with ``id`` + ``text`` / ``document``.
        supported_threshold: Overlap cutoff for supported (default 0.55).
        weak_threshold: Overlap cutoff for weak (default 0.30).

    Returns:
        :class:`ClaimCheckReport`.
    """
    if not 0.0 <= weak_threshold <= supported_threshold <= 1.0:
        raise ValueError(
            "require 0 <= weak_threshold <= supported_threshold <= 1"
        )

    reasons: list[str] = []
    answer = answer or ""

    if not answer.strip():
        return ClaimCheckReport(
            claims=[],
            entities=[],
            n_supported=0,
            n_weak=0,
            n_unsupported=0,
            n_missing_entities=0,
            decision="abstain",
            reasons=["empty answer"],
            notes=_STUB_NOTES,
        )

    source_rows: list[tuple[str, set[str]]] = []
    source_texts_cf: list[str] = []
    union: set[str] = set()
    for i, src in enumerate(sources):
        sid, text = _source_text(src)
        if sid is None:
            sid = f"doc-{i}"
        words = set(_content_words(text))
        union |= words
        source_rows.append((sid, words))
        source_texts_cf.append(text.casefold())

    claim_texts = split_claims(answer)
    claims: list[ClaimResult] = []
    n_supported = n_weak = n_unsupported = 0
    for ct in claim_texts:
        overlap, best_id = _claim_overlap(ct, union, source_rows)
        if overlap >= supported_threshold:
            status: Literal["supported", "weak", "unsupported"] = "supported"
            n_supported += 1
        elif overlap >= weak_threshold:
            status = "weak"
            n_weak += 1
        else:
            status = "unsupported"
            n_unsupported += 1
        claims.append(
            ClaimResult(
                text=ct,
                status=status,
                overlap=round(overlap, 4),
                best_source_id=best_id,
            )
        )

    raw_entities = extract_sensitive_tokens(answer)
    entities: list[EntityHit] = []
    n_missing = 0
    for token, kind in raw_entities:
        found = _entity_in_sources(token, source_texts_cf)
        if not found:
            n_missing += 1
        entities.append(
            EntityHit(
                token=token,
                kind=kind,  # type: ignore[arg-type]
                found_in_sources=found,
            )
        )

    if n_unsupported > 0:
        reasons.append(f"{n_unsupported} unsupported claim(s)")
    if n_missing > 0:
        missing = [e.token for e in entities if not e.found_in_sources]
        reasons.append(f"missing entities: {', '.join(missing)}")
    if n_weak > 0 and n_unsupported == 0 and n_missing == 0:
        reasons.append(f"{n_weak} weak claim(s)")

    if n_unsupported > 0 or n_missing > 0:
        decision: Literal["pass", "rewrite", "abstain"] = "abstain"
    elif n_weak > 0:
        decision = "rewrite"
    else:
        decision = "pass"
        if not reasons:
            reasons.append("all claims supported; no missing entities")

    return ClaimCheckReport(
        claims=claims,
        entities=entities,
        n_supported=n_supported,
        n_weak=n_weak,
        n_unsupported=n_unsupported,
        n_missing_entities=n_missing,
        decision=decision,
        reasons=reasons,
        notes=_STUB_NOTES,
    )


def report_to_dict(report: ClaimCheckReport) -> dict[str, Any]:
    """Serialize a :class:`ClaimCheckReport` to a JSON-friendly dict."""
    return {
        "decision": report.decision,
        "reasons": list(report.reasons),
        "n_supported": report.n_supported,
        "n_weak": report.n_weak,
        "n_unsupported": report.n_unsupported,
        "n_missing_entities": report.n_missing_entities,
        "claims": [
            {
                "text": c.text,
                "status": c.status,
                "overlap": c.overlap,
                "best_source_id": c.best_source_id,
            }
            for c in report.claims
        ],
        "entities": [
            {
                "token": e.token,
                "kind": e.kind,
                "found_in_sources": e.found_in_sources,
            }
            for e in report.entities
        ],
        "notes": report.notes,
    }


def format_claim_check_report(report: ClaimCheckReport) -> str:
    """Human-readable claim-check summary."""
    lines = [
        f"decision: {report.decision}",
        f"reasons: {'; '.join(report.reasons) if report.reasons else '(none)'}",
        (
            f"claims: {report.n_supported} supported, "
            f"{report.n_weak} weak, {report.n_unsupported} unsupported"
        ),
        f"missing_entities: {report.n_missing_entities}",
    ]
    for c in report.claims:
        sid = c.best_source_id or "-"
        lines.append(
            f"  [{c.status}] overlap={c.overlap:.2f} <- {sid}: {c.text}"
        )
    missing = [e for e in report.entities if not e.found_in_sources]
    if missing:
        lines.append("missing:")
        for e in missing:
            lines.append(f"  - {e.kind}: {e.token}")
    present = [e for e in report.entities if e.found_in_sources]
    if present:
        lines.append("entities_ok:")
        for e in present:
            lines.append(f"  + {e.kind}: {e.token}")
    lines.append(f"notes: {report.notes}")
    return "\n".join(lines) + "\n"


__all__ = [
    "ClaimCheckReport",
    "ClaimResult",
    "EntityHit",
    "check_claims",
    "extract_sensitive_tokens",
    "format_claim_check_report",
    "report_to_dict",
    "split_claims",
]
