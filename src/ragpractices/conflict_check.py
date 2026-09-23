"""Pre-answer source conflict detector (numbers + lightweight negation).

Educational heuristic that flags when retrieved sources disagree—especially on
**numbers**—before generation. Complements post-answer ``claim_check``,
``cite_spans``, aggregate ``groundedness``, and index ``canaries``.

This is **not** a production NLI / contradiction model. Use dedicated
contradiction / NLI judges when faithfulness truly matters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Sequence

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)

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

# Negation cues are kept out of stopwords so phrase streams can still drop them
# separately when building content n-grams, while neighborhood scans see them.
_NEGATION_CUES = frozenset(
    {"not", "no", "never", "cannot", "cant", "without"}
)

_STRONG_KEYWORDS = frozenset(
    {
        "day",
        "days",
        "hour",
        "hours",
        "minute",
        "minutes",
        "percent",
        "week",
        "weeks",
        "month",
        "months",
        "year",
        "years",
        "dollar",
        "usd",
    }
)
_STRONG_SYMBOLS = ("%", "€", "£")

# Numbers: optional commas, optional decimal, optional trailing %
_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9/.-])"
    r"("
    r"\d{1,3}(?:,\d{3})+(?:\.\d+)?%?"
    r"|\d+\.\d+%?"
    r"|\d+%?"
    r")"
    r"(?![A-Za-z0-9/.-])"
)

_YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")

_CONTEXT_CHARS = 40
_CONTEXT_TOKENS = 6
_MIN_SHARED_CONTENT = 2
_NEGATION_WINDOW = 3

_STUB_NOTES = (
    "Educational heuristic source-conflict check (number context buckets + "
    "lightweight negation polarity). Not a production NLI / contradiction "
    "model—use dedicated contradiction detection for real faithfulness."
)


@dataclass
class NumberMention:
    """One numeric surface form found in a source (or answer)."""

    value: str  # normalized surface e.g. "30", "3.14"
    raw: str
    source_id: str
    context: str  # short window around the number


@dataclass
class Conflict:
    """One flagged disagreement among sources (and optionally the answer)."""

    kind: Literal["number", "negation"]
    summary: str
    source_ids: list[str]
    details: list[str] = field(default_factory=list)


@dataclass
class ConflictReport:
    """Aggregate pre-answer conflict check report."""

    conflicts: list[Conflict]
    number_mentions: list[NumberMention]
    n_sources: int
    decision: Literal["ok", "conflict"]
    reasons: list[str]
    notes: str = _STUB_NOTES


def _tokenize(text: str) -> list[str]:
    t = text.casefold()
    for apo in ("'", "\u2019"):
        t = t.replace(f"can{apo}t", "cannot")
    return _TOKEN_RE.findall(t)


def _content_words(text: str) -> list[str]:
    return [
        t
        for t in _tokenize(text)
        if t not in _STOPWORDS and t not in _NEGATION_CUES and len(t) > 1
    ]


def _source_text(item: str | dict[str, Any]) -> tuple[str, str]:
    """Return ``(source_id, text)``; caller supplies index for ``doc-{i}``."""
    if isinstance(item, str):
        return "", item
    if isinstance(item, dict):
        sid = item.get("id", item.get("index"))
        text = str(
            item.get("text")
            or item.get("document")
            or item.get("snippet")
            or ""
        )
        return (str(sid) if sid is not None else ""), text
    raise TypeError(f"source must be str or dict, got {type(item)}")


def _normalize_sources(
    sources: Sequence[dict[str, Any] | str],
) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for i, item in enumerate(sources):
        sid, text = _source_text(item)
        if not sid:
            sid = f"doc-{i}"
        out.append((sid, text))
    return out


def _normalize_number(raw: str) -> str | None:
    """Normalize a numeric surface; skip bare years."""
    s = raw.strip()
    if not s:
        return None
    bare = s.rstrip("%").replace(",", "")
    if _YEAR_RE.match(bare):
        return None
    return bare




def _window_context(text: str, start: int, end: int) -> str:
    lo = max(0, start - _CONTEXT_CHARS)
    hi = min(len(text), end + _CONTEXT_CHARS)
    return text[lo:hi].strip()




def _strong_markers(context: str, content: Sequence[str]) -> set[str]:
    markers = {w for w in content if w in _STRONG_KEYWORDS}
    ctx = context.casefold()
    for sym in _STRONG_SYMBOLS:
        if sym in context or (sym == "%" and "%" in ctx):
            markers.add(sym)
    # percent word already covered; also catch "%" via raw context
    if "%" in context:
        markers.add("%")
    if "€" in context:
        markers.add("€")
    if "£" in context:
        markers.add("£")
    return markers


def extract_number_mentions(
    sources: Sequence[dict[str, Any] | str],
) -> list[NumberMention]:
    """Extract integer/decimal/percent mentions from each source."""
    mentions: list[NumberMention] = []
    for sid, text in _normalize_sources(sources):
        for m in _NUMBER_RE.finditer(text):
            raw = m.group(1)
            value = _normalize_number(raw)
            if value is None:
                continue
            ctx = _window_context(text, m.start(1), m.end(1))
            mentions.append(
                NumberMention(
                    value=value,
                    raw=raw,
                    source_id=sid,
                    context=ctx,
                )
            )
    return mentions


def find_number_conflicts(mentions: list[NumberMention]) -> list[Conflict]:
    """Flag different numeric values that share similar local context.

    Two mentions conflict when their normalized values differ, they come from
    different sources, and either:

    - their context windows share ≥2 content words, or
    - both windows share a strong keyword/symbol (day/days, percent/%, …).
    """
    if len(mentions) < 2:
        return []

    features: list[tuple[list[str], set[str]]] = []
    for m in mentions:
        content = _content_words(m.context)
        markers = _strong_markers(m.context, content)
        features.append((content, markers))

    conflicts: list[Conflict] = []
    seen_pairs: set[tuple[str, str, str, str]] = set()

    for i, a in enumerate(mentions):
        content_a, markers_a = features[i]
        set_a = set(content_a)
        for j in range(i + 1, len(mentions)):
            b = mentions[j]
            if a.source_id == b.source_id:
                continue
            if a.value == b.value:
                continue
            content_b, markers_b = features[j]
            set_b = set(content_b)
            shared = set_a & set_b
            shared_strong = markers_a & markers_b
            if len(shared) < _MIN_SHARED_CONTENT and not shared_strong:
                continue
            key = tuple(
                sorted([a.source_id, b.source_id]) + sorted([a.value, b.value])
            )
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            detail_bits = [
                f"{a.source_id}: {a.raw!r} in {a.context!r}",
                f"{b.source_id}: {b.raw!r} in {b.context!r}",
            ]
            if shared_strong:
                detail_bits.append(
                    f"shared_keywords: {', '.join(sorted(shared_strong))}"
                )
            elif shared:
                detail_bits.append(
                    f"shared_content: {', '.join(sorted(shared))}"
                )
            conflicts.append(
                Conflict(
                    kind="number",
                    summary=(
                        f"Conflicting numbers {a.value} vs {b.value} "
                        f"near similar context"
                    ),
                    source_ids=sorted({a.source_id, b.source_id}),
                    details=detail_bits,
                )
            )
    return conflicts


def _content_ngrams(tokens: Sequence[str]) -> dict[tuple[str, ...], list[int]]:
    """Map content bigrams/trigrams to start indices in the full token list.

    Content stream skips stopwords and negation cues; indices point at the
    first token of the n-gram in the **full** token sequence.
    """
    # Build (full_index, content_token) stream
    content_idx: list[tuple[int, str]] = []
    for i, tok in enumerate(tokens):
        if tok in _STOPWORDS or tok in _NEGATION_CUES or len(tok) <= 1:
            continue
        content_idx.append((i, tok))

    found: dict[tuple[str, ...], list[int]] = {}
    n = len(content_idx)
    for size in (2, 3):
        for i in range(n - size + 1):
            gram = tuple(content_idx[j][1] for j in range(i, i + size))
            start_full = content_idx[i][0]
            found.setdefault(gram, []).append(start_full)
    return found


def _phrase_negated(
    tokens: Sequence[str], start_full: int, gram_len: int
) -> bool:
    """True if a negation cue is within ``_NEGATION_WINDOW`` of the phrase."""
    # Content n-gram of length gram_len spans from start_full to the
    # gram_len-th content token; approximate end as start_full + 2*gram_len + 2
    # and scan a neighborhood.
    # Find end: walk forward counting content tokens
    content_seen = 0
    end_full = start_full
    for i in range(start_full, len(tokens)):
        tok = tokens[i]
        if tok in _STOPWORDS or tok in _NEGATION_CUES or len(tok) <= 1:
            end_full = i
            continue
        content_seen += 1
        end_full = i
        if content_seen >= gram_len:
            break
    lo = max(0, start_full - _NEGATION_WINDOW)
    hi = min(len(tokens), end_full + _NEGATION_WINDOW + 1)
    for i in range(lo, hi):
        if tokens[i] in _NEGATION_CUES:
            return True
    return False


def find_negation_conflicts(
    sources: Sequence[dict[str, Any] | str],
) -> list[Conflict]:
    """Flag shared content phrases with opposite polarity across sources.

    Conservative: only shared content bigrams/trigrams that appear in ≥2
    sources, where one occurrence is near a negation cue and another is not.
    """
    normalized = _normalize_sources(sources)
    if len(normalized) < 2:
        return []

    # gram -> list of (source_id, start_full, tokens, negated)
    occurrences: dict[
        tuple[str, ...], list[tuple[str, int, list[str], bool]]
    ] = {}

    for sid, text in normalized:
        tokens = _tokenize(text)
        grams = _content_ngrams(tokens)
        for gram, starts in grams.items():
            for start in starts:
                neg = _phrase_negated(tokens, start, len(gram))
                occurrences.setdefault(gram, []).append(
                    (sid, start, tokens, neg)
                )

    # Prefer longer phrases; one conflict per source-pair polarity clash.
    candidates: list[tuple[int, tuple[str, ...], set[str], set[str]]] = []
    for gram, occs in occurrences.items():
        source_ids = {o[0] for o in occs}
        if len(source_ids) < 2:
            continue
        negated_sids = {o[0] for o in occs if o[3]}
        plain_sids = {o[0] for o in occs if not o[3]}
        if not negated_sids or not plain_sids:
            continue
        # Prefer cross-source polarity: at least one source only affirms
        # and one only negates when sets overlap on a source.
        only_neg = negated_sids - plain_sids
        only_plain = plain_sids - negated_sids
        if not only_neg or not only_plain:
            # If every source that negates also affirms (same doc both ways),
            # skip unless other sources disagree purely.
            if not (negated_sids and plain_sids and negated_sids != plain_sids):
                continue
        candidates.append(
            (len(gram), gram, only_plain or plain_sids, only_neg or negated_sids)
        )

    candidates.sort(key=lambda x: (-x[0], x[1]))
    conflicts: list[Conflict] = []
    seen_pairs: set[frozenset[str]] = set()
    seen_grams: list[tuple[str, ...]] = []

    for _n, gram, plain_sids, negated_sids in candidates:
        involved = frozenset(plain_sids | negated_sids)
        # Skip shorter grams subsumed by an already-emitted longer gram
        subsumed = False
        for prev in seen_grams:
            if len(prev) >= len(gram):
                # consecutive subsequence check
                for i in range(len(prev) - len(gram) + 1):
                    if prev[i : i + len(gram)] == gram:
                        subsumed = True
                        break
            if subsumed:
                break
        if subsumed:
            continue
        if involved in seen_pairs:
            continue
        seen_pairs.add(involved)
        seen_grams.append(gram)
        phrase = " ".join(gram)
        details = [
            f"phrase: {phrase!r}",
            f"negated_in: {', '.join(sorted(negated_sids))}",
            f"affirmed_in: {', '.join(sorted(plain_sids))}",
        ]
        conflicts.append(
            Conflict(
                kind="negation",
                summary=(
                    f"Negation conflict on {phrase!r}: "
                    f"affirmed in {', '.join(sorted(plain_sids))}; "
                    f"negated in {', '.join(sorted(negated_sids))}"
                ),
                source_ids=sorted(involved),
                details=details,
            )
        )
    return conflicts


def _answer_number_side_conflicts(
    answer: str,
    source_mentions: list[NumberMention],
    number_conflicts: list[Conflict],
) -> list[Conflict]:
    """If answer picks a number that conflicts with other sources, note it."""
    if not answer or not number_conflicts:
        return []

    answer_mentions = extract_number_mentions(
        [{"id": "answer", "text": answer}]
    )
    answer_values = {m.value for m in answer_mentions}
    if not answer_values:
        return []

    extra: list[Conflict] = []
    for c in number_conflicts:
        if c.kind != "number":
            continue
        # Parse values from summary "Conflicting numbers X vs Y ..."
        # Prefer details raw values from involved source mentions
        involved_values: set[str] = set()
        for m in source_mentions:
            if m.source_id in c.source_ids:
                # Only values that participate in this conflict pair
                involved_values.add(m.value)
        # Narrow to values mentioned in conflict details if possible
        detail_vals = set()
        for d in c.details:
            for m in source_mentions:
                if m.source_id in c.source_ids and (
                    repr(m.raw) in d or m.raw in d
                ):
                    detail_vals.add(m.value)
        vals = detail_vals or involved_values
        sided = answer_values & vals
        if not sided:
            continue
        other = vals - sided
        if not other:
            continue
        extra.append(
            Conflict(
                kind="number",
                summary=(
                    f"Answer uses {', '.join(sorted(sided))} while sources "
                    f"also report conflicting {', '.join(sorted(other))}"
                ),
                source_ids=list(c.source_ids) + ["answer"],
                details=c.details
                + [f"answer_values: {', '.join(sorted(sided))}"],
            )
        )
    return extra


def check_conflicts(
    sources: Sequence[dict[str, Any] | str],
    *,
    answer: str | None = None,
) -> ConflictReport:
    """Check retrieved sources for number / negation conflicts.

    Optional ``answer``: if provided and it sides with one camp in an existing
    number conflict, an additional conflict noting that preference is added
    (decision remains ``conflict``).

    Empty ``sources`` → ``decision="ok"`` with reason ``no sources to compare``
    (avoids blocking empty pipelines).
    """
    normalized = _normalize_sources(sources)
    n_sources = len(normalized)
    reasons: list[str] = []

    if n_sources == 0:
        return ConflictReport(
            conflicts=[],
            number_mentions=[],
            n_sources=0,
            decision="ok",
            reasons=["no sources to compare"],
            notes=_STUB_NOTES,
        )

    mentions = extract_number_mentions(sources)
    number_conflicts = find_number_conflicts(mentions)
    negation_conflicts = find_negation_conflicts(sources)

    conflicts: list[Conflict] = list(number_conflicts) + list(
        negation_conflicts
    )

    if answer is not None and str(answer).strip():
        extra = _answer_number_side_conflicts(
            str(answer), mentions, number_conflicts
        )
        conflicts.extend(extra)

    if conflicts:
        decision: Literal["ok", "conflict"] = "conflict"
        n_num = sum(1 for c in conflicts if c.kind == "number")
        n_neg = sum(1 for c in conflicts if c.kind == "negation")
        if n_num:
            reasons.append(f"{n_num} number conflict(s)")
        if n_neg:
            reasons.append(f"{n_neg} negation conflict(s)")
    else:
        decision = "ok"
        reasons.append("no conflicts detected among sources")

    return ConflictReport(
        conflicts=conflicts,
        number_mentions=mentions,
        n_sources=n_sources,
        decision=decision,
        reasons=reasons,
        notes=_STUB_NOTES,
    )


def report_to_dict(report: ConflictReport) -> dict[str, Any]:
    """Serialize a :class:`ConflictReport` to a JSON-friendly dict."""
    return {
        "decision": report.decision,
        "reasons": list(report.reasons),
        "n_sources": report.n_sources,
        "conflicts": [
            {
                "kind": c.kind,
                "summary": c.summary,
                "source_ids": list(c.source_ids),
                "details": list(c.details),
            }
            for c in report.conflicts
        ],
        "number_mentions": [
            {
                "value": m.value,
                "raw": m.raw,
                "source_id": m.source_id,
                "context": m.context,
            }
            for m in report.number_mentions
        ],
        "notes": report.notes,
    }


def format_conflict_report(report: ConflictReport) -> str:
    """Human-readable conflict-check summary."""
    lines = [
        f"decision: {report.decision}",
        f"reasons: {'; '.join(report.reasons) if report.reasons else '(none)'}",
        f"n_sources: {report.n_sources}",
        f"conflicts: {len(report.conflicts)}",
        f"number_mentions: {len(report.number_mentions)}",
    ]
    for c in report.conflicts:
        lines.append(f"  [{c.kind}] {c.summary}")
        lines.append(f"    sources: {', '.join(c.source_ids)}")
        for d in c.details:
            lines.append(f"    - {d}")
    if report.number_mentions and report.conflicts:
        lines.append("mentions:")
        for m in report.number_mentions:
            lines.append(
                f"  - {m.source_id}: {m.raw} (={m.value}) :: {m.context!r}"
            )
    lines.append(f"notes: {report.notes}")
    return "\n".join(lines) + "\n"


__all__ = [
    "Conflict",
    "ConflictReport",
    "NumberMention",
    "check_conflicts",
    "extract_number_mentions",
    "find_negation_conflicts",
    "find_number_conflicts",
    "format_conflict_report",
    "report_to_dict",
]
