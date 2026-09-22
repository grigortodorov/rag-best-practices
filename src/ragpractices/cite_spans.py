"""Citation span verifier: quotes and numeric markers vs sources (stdlib only).

Educational / heuristic checks—not an NLI entailment judge. Verifies that
quoted spans in an answer appear (substring or whitespace-normalized) in
provided sources, and that ``[n]`` / ``【n】`` markers point at real sources
(1-based index into the sources list).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Sequence

# Numeric markers: [1] or fullwidth 【1】
_MARKER_RE = re.compile(r"\[(\d+)\]|【(\d+)】")
# Double-quoted spans (straight or curly)
_QUOTE_RE = re.compile(r'"([^"]+)"|\u201c([^\u201d]+)\u201d')


@dataclass
class QuoteCheck:
    """One quoted span checked against sources."""

    quote: str
    supported: bool
    matched_source_id: str | None = None


@dataclass
class CiteSpanReport:
    """Aggregate citation-span verification report."""

    supported_quotes: list[QuoteCheck] = field(default_factory=list)
    unsupported_quotes: list[QuoteCheck] = field(default_factory=list)
    unused_sources: list[str] = field(default_factory=list)
    orphan_citations: list[int] = field(default_factory=list)
    cited_indices: list[int] = field(default_factory=list)
    n_quotes: int = 0
    n_supported: int = 0
    notes: str = (
        "Educational heuristic citation-span check (substring / whitespace "
        "normalize). Not an NLI entailment judge or production auditor."
    )

    @property
    def all_supported(self) -> bool:
        return self.n_supported == self.n_quotes and not self.orphan_citations


def _normalize_ws(text: str) -> str:
    return " ".join(text.split()).casefold()


def _source_text(src: dict[str, Any] | str) -> str:
    if isinstance(src, str):
        return src
    return str(src.get("text") or src.get("document") or src.get("snippet") or "")


def _source_id(src: dict[str, Any] | str, index: int) -> str:
    if isinstance(src, str):
        return f"doc-{index}"
    return str(src.get("id", f"doc-{index}"))


def extract_quotes(answer: str) -> list[str]:
    """Extract double-quoted spans from ``answer`` (heuristic)."""
    found: list[str] = []
    for m in _QUOTE_RE.finditer(answer):
        q = next((g for g in m.groups() if g is not None), "")
        q = q.strip()
        if q:
            found.append(q)
    return found


def extract_citation_indices(answer: str) -> list[int]:
    """Extract 1-based citation indices from ``[n]`` / ``【n】`` markers."""
    indices: list[int] = []
    seen: set[int] = set()
    for m in _MARKER_RE.finditer(answer):
        raw = m.group(1) or m.group(2)
        n = int(raw)
        if n not in seen:
            seen.add(n)
            indices.append(n)
    return indices


def _quote_supported(
    quote: str, sources: Sequence[dict[str, Any] | str]
) -> tuple[bool, str | None]:
    q_raw = quote
    q_norm = _normalize_ws(quote)
    if not q_norm:
        return False, None
    for i, src in enumerate(sources):
        text = _source_text(src)
        sid = _source_id(src, i)
        if q_raw in text:
            return True, sid
        if q_norm and q_norm in _normalize_ws(text):
            return True, sid
    return False, None


def verify_citation_spans(
    answer: str,
    sources: Sequence[dict[str, Any] | str],
) -> CiteSpanReport:
    """Verify quoted spans and numeric citation markers against ``sources``.

    - **Supported quotes:** substring or whitespace-normalized match in any
      source text.
    - **Unsupported quotes:** no source contains the quote (hallucinated span).
    - **Unused sources:** provided sources never cited by ``[n]`` / ``【n】``
      (1-based) and never matched by a supported quote.
    - **Orphan citations:** marker index with no corresponding source.

    Args:
        answer: Model answer text possibly containing quotes and ``[n]``.
        sources: Ordered source list (index ``i`` ↔ marker ``[i+1]``).

    Returns:
        :class:`CiteSpanReport` with supported/unsupported quotes and orphans.
    """
    quotes = extract_quotes(answer)
    cited = extract_citation_indices(answer)
    n_sources = len(sources)

    supported: list[QuoteCheck] = []
    unsupported: list[QuoteCheck] = []
    matched_ids: set[str] = set()
    cited_source_ids: set[str] = set()

    for q in quotes:
        ok, sid = _quote_supported(q, sources)
        check = QuoteCheck(quote=q, supported=ok, matched_source_id=sid)
        if ok:
            supported.append(check)
            if sid:
                matched_ids.add(sid)
        else:
            unsupported.append(check)

    orphans: list[int] = []
    for idx in cited:
        if idx < 1 or idx > n_sources:
            orphans.append(idx)
        else:
            cited_source_ids.add(_source_id(sources[idx - 1], idx - 1))

    used_ids = matched_ids | cited_source_ids
    unused: list[str] = []
    for i, src in enumerate(sources):
        sid = _source_id(src, i)
        if sid not in used_ids:
            unused.append(sid)

    return CiteSpanReport(
        supported_quotes=supported,
        unsupported_quotes=unsupported,
        unused_sources=unused,
        orphan_citations=orphans,
        cited_indices=cited,
        n_quotes=len(quotes),
        n_supported=len(supported),
    )


def report_to_dict(report: CiteSpanReport) -> dict[str, Any]:
    """Serialize a :class:`CiteSpanReport` to a JSON-friendly dict."""
    return {
        "n_quotes": report.n_quotes,
        "n_supported": report.n_supported,
        "all_supported": report.all_supported,
        "supported_quotes": [
            {
                "quote": q.quote,
                "supported": q.supported,
                "matched_source_id": q.matched_source_id,
            }
            for q in report.supported_quotes
        ],
        "unsupported_quotes": [
            {
                "quote": q.quote,
                "supported": q.supported,
                "matched_source_id": q.matched_source_id,
            }
            for q in report.unsupported_quotes
        ],
        "unused_sources": list(report.unused_sources),
        "orphan_citations": list(report.orphan_citations),
        "cited_indices": list(report.cited_indices),
        "notes": report.notes,
    }


def format_cite_span_report(report: CiteSpanReport) -> str:
    """Human-readable citation-span summary."""
    lines = [
        f"quotes: {report.n_supported}/{report.n_quotes} supported",
        f"orphans: {report.orphan_citations or '(none)'}",
        f"unused_sources: {report.unused_sources or '(none)'}",
        f"cited_indices: {report.cited_indices or '(none)'}",
    ]
    for q in report.supported_quotes:
        lines.append(f"  + supported: {q.quote!r} <- {q.matched_source_id}")
    for q in report.unsupported_quotes:
        lines.append(f"  - unsupported: {q.quote!r}")
    lines.append(f"notes: {report.notes}")
    return "\n".join(lines) + "\n"


__all__ = [
    "CiteSpanReport",
    "QuoteCheck",
    "extract_citation_indices",
    "extract_quotes",
    "format_cite_span_report",
    "report_to_dict",
    "verify_citation_spans",
]
