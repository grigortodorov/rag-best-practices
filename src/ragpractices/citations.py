"""Citation formatting helpers for grounded RAG answers (stdlib only)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

CitationStyle = Literal["numeric", "bracketed"]

_NUMERIC_MARKER_RE = re.compile(r"\[(\d+)\]")
_BRACKETED_AT_RE = re.compile(r"\[@([^\]]+)\]")


@dataclass
class Citation:
    """A single source citation used when formatting grounded answers."""

    id: str
    title: str = ""
    snippet: str = ""
    score: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, fallback_index: int = 0) -> Citation:
        """Build a Citation from a loose source / retrieved dict."""
        cid = raw.get("id")
        if cid is None and "index" in raw:
            cid = str(raw["index"])
        if cid is None:
            cid = f"src-{fallback_index}"
        title = str(raw.get("title") or "")
        snippet = str(
            raw.get("snippet")
            or raw.get("document")
            or raw.get("text")
            or ""
        )
        score = raw.get("score")
        score_f = float(score) if score is not None else None
        meta = {k: v for k, v in raw.items() if k not in {"id", "index", "title", "snippet", "document", "text", "score"}}
        return cls(id=str(cid), title=title, snippet=snippet, score=score_f, meta=meta)


def _as_citations(sources: list[dict[str, Any]]) -> list[Citation]:
    return [Citation.from_dict(s, fallback_index=i) for i, s in enumerate(sources)]


def build_sources_block(
    sources: list[dict[str, Any]],
    *,
    style: CitationStyle = "numeric",
) -> str:
    """Render a Sources appendix from source dicts.

    ``style="numeric"`` uses ``(1) title — snippet`` lines.
    ``style="bracketed"`` uses ``[id] title — snippet`` lines.
    """
    if style not in ("numeric", "bracketed"):
        raise ValueError("style must be 'numeric' or 'bracketed'")

    citations = _as_citations(sources)
    if not citations:
        return "Sources:\n(none)"

    lines = ["Sources:"]
    for i, c in enumerate(citations, start=1):
        label = f"({i})" if style == "numeric" else f"[{c.id}]"
        title = c.title.strip()
        snippet = c.snippet.strip()
        # Trim long snippets for the appendix
        if len(snippet) > 160:
            snippet = snippet[:157].rstrip() + "..."
        parts: list[str] = [label]
        if title:
            parts.append(title)
        if snippet:
            if title:
                parts.append("—")
            parts.append(snippet)
        lines.append(" ".join(parts))
    return "\n".join(lines)


def format_inline_citations(
    answer: str,
    sources: list[dict[str, Any]],
    *,
    style: CitationStyle = "numeric",
) -> str:
    """Format an answer with inline citations.

    - ``style="numeric"``: replace ``[n]`` markers with ``(n)`` (1-based into
      ``sources``). If no ``[n]`` markers exist, append ``(1) (2) …`` for all
      sources, then callers typically add a Sources appendix separately.
    - ``style="bracketed"``: replace ``[@id]`` with ``[id]``; if none present,
      append ``[id]`` for each source id.
    """
    if style not in ("numeric", "bracketed"):
        raise ValueError("style must be 'numeric' or 'bracketed'")

    citations = _as_citations(sources)
    text = answer.rstrip()

    if style == "numeric":
        def _repl(m: re.Match[str]) -> str:
            n = int(m.group(1))
            if 1 <= n <= len(citations):
                return f"({n})"
            return m.group(0)

        if _NUMERIC_MARKER_RE.search(text):
            return _NUMERIC_MARKER_RE.sub(_repl, text)

        if citations:
            refs = " ".join(f"({i})" for i in range(1, len(citations) + 1))
            return f"{text} {refs}".rstrip() if text else refs
        return text

    # bracketed
    def _repl_at(m: re.Match[str]) -> str:
        return f"[{m.group(1)}]"

    if _BRACKETED_AT_RE.search(text):
        return _BRACKETED_AT_RE.sub(_repl_at, text)

    # Also accept bare [id] already present — leave as-is; append missing ids
    existing = set(re.findall(r"\[([^\]]+)\]", text))
    missing = [c.id for c in citations if c.id not in existing]
    if missing:
        refs = " ".join(f"[{mid}]" for mid in missing)
        return f"{text} {refs}".rstrip() if text else refs
    return text


def attach_citations(
    answer: str,
    retrieved: list[dict[str, Any]],
    *,
    style: CitationStyle = "numeric",
) -> dict[str, str]:
    """Attach citations to an answer and build a Sources appendix.

    ``retrieved`` items may use ``id``/``index``, ``document``/``text``, and
    optional ``score`` / ``title`` / ``snippet``.

    Returns:
        ``{"answer", "sources_block", "full_text"}`` where ``full_text`` is
        the formatted answer plus the sources block.
    """
    sources = list(retrieved)
    formatted = format_inline_citations(answer, sources, style=style)
    block = build_sources_block(sources, style=style)
    full = f"{formatted}\n\n{block}" if formatted else block
    return {
        "answer": formatted,
        "sources_block": block,
        "full_text": full,
    }
