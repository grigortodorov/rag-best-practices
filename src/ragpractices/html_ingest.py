"""HTML → text ingest and content hashing (stdlib only).

Uses :mod:`html.parser` — no BeautifulSoup or other runtime deps.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from ragpractices.ingest import Document, _document_id, content_hash


_BLOCK_TAGS = frozenset(
    {
        "p",
        "div",
        "section",
        "article",
        "header",
        "footer",
        "aside",
        "nav",
        "main",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "ul",
        "ol",
        "tr",
        "br",
        "hr",
        "blockquote",
        "pre",
        "table",
    }
)
_SKIP_TAGS = frozenset({"script", "style", "noscript", "template", "title"})


class _HTMLTextExtractor(HTMLParser):
    """Collect visible text, inserting newlines around block elements."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if t in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if t in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if data:
            self._chunks.append(data)

    def get_text(self) -> str:
        raw = "".join(self._chunks)
        # Collapse whitespace per line, then squeeze blank lines
        lines = [" ".join(line.split()) for line in raw.splitlines()]
        lines = [ln for ln in lines if ln]
        return "\n".join(lines)


def html_to_text(html: str) -> str:
    """Extract readable text from an HTML string via :class:`html.parser.HTMLParser`.

    Skips ``script`` / ``style`` content. Inserts newlines around common
    block tags. Collapses runs of whitespace.
    """
    if not html:
        return ""
    parser = _HTMLTextExtractor()
    parser.feed(html)
    parser.close()
    return parser.get_text()



def load_html_file(path: str | Path, *, root: Path | None = None) -> Document:
    """Load an HTML file into a :class:`Document` with text extracted.

    ``meta`` includes ``content_type: html`` and ``content_hash`` (sha256 of
    the extracted text).
    """
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    text = html_to_text(raw)
    meta: dict[str, Any] = {
        "content_type": "html",
        "content_hash": content_hash(text),
    }
    # Optional <title>
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = " ".join(title_match.group(1).split())
        if title:
            meta["title"] = title
    return Document(
        id=_document_id(p, root=root),
        path=str(p),
        text=text,
        meta=meta,
    )
