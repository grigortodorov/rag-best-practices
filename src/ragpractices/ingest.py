"""Document ingest helpers for building a small local corpus (stdlib only)."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


_SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}

_FRONT_MATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)",
    re.DOTALL,
)


@dataclass
class Document:
    """A loaded text document ready for chunking or hybrid search."""

    id: str
    path: str
    text: str
    meta: dict[str, Any] = field(default_factory=dict)


def _document_id(path: Path, *, root: Path | None = None) -> str:
    """Derive a stable id from the path stem or a relative path."""
    if root is not None:
        try:
            rel = path.resolve().relative_to(root.resolve())
            return rel.as_posix()
        except ValueError:
            pass
    return path.stem or path.name


def _is_hidden_or_skip(path: Path, *, root: Path) -> bool:
    """True if any path component under ``root`` is hidden or a skip dir."""
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        rel = path
    for part in rel.parts:
        if part in (".", ".."):
            continue
        if part.startswith("."):
            return True
        if part in _SKIP_DIR_NAMES:
            return True
    return False


def _parse_simple_yaml_front_matter(block: str) -> dict[str, Any]:
    """Parse a minimal ``key: value`` YAML front-matter block into a dict.

    Only handles flat scalar lines (no nested structures). Unparseable
    lines are skipped. Keys and string values are stripped; booleans and
    integers are coerced when obvious.
    """
    meta: dict[str, Any] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        lower = value.lower()
        if lower in ("true", "false"):
            meta[key] = lower == "true"
        else:
            try:
                meta[key] = int(value)
            except ValueError:
                meta[key] = value
    return meta


def _strip_front_matter(text: str) -> tuple[str, dict[str, Any]]:
    """If ``text`` starts with a ``---`` YAML block, strip it into meta."""
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return text, {}
    meta = _parse_simple_yaml_front_matter(match.group(1))
    body = text[match.end() :]
    return body, meta


def load_text_file(path: str | Path, *, root: Path | None = None) -> Document:
    """Load a UTF-8 text file into a :class:`Document`.

    ``id`` is the file stem, or the path relative to ``root`` when given
    (useful for directory loads).
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    return Document(
        id=_document_id(p, root=root),
        path=str(p),
        text=text,
        meta={},
    )


def load_markdown_file(path: str | Path, *, root: Path | None = None) -> Document:
    """Load a UTF-8 Markdown file, optionally stripping YAML front matter.

    A leading ``---`` … ``---`` block is parsed into ``meta`` (flat
    ``key: value`` lines only) and removed from ``text``.
    """
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    body, meta = _strip_front_matter(raw)
    return Document(
        id=_document_id(p, root=root),
        path=str(p),
        text=body,
        meta=meta,
    )


def _iter_files(root: Path, patterns: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for candidate in sorted(root.glob(pattern)):
            if not candidate.is_file():
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            if _is_hidden_or_skip(candidate, root=root):
                continue
            seen.add(resolved)
            files.append(candidate)
    return files


def load_path(
    path: str | Path,
    *,
    glob: str | None = None,
) -> list[Document]:
    """Load a single file or all matching files under a directory.

    When ``path`` is a directory and ``glob`` is omitted, includes
    ``**/*.txt`` and ``**/*.md``. Hidden directories and common virtualenv
    / cache folders are skipped. Markdown files use front-matter stripping;
    other extensions are loaded as plain text.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"path does not exist: {p}")

    if p.is_file():
        if p.suffix.lower() in {".md", ".markdown"}:
            return [load_markdown_file(p)]
        return [load_text_file(p)]

    if not p.is_dir():
        raise ValueError(f"path is neither a file nor a directory: {p}")

    patterns = [glob] if glob else ["**/*.txt", "**/*.md"]
    docs: list[Document] = []
    for file_path in _iter_files(p, patterns):
        if file_path.suffix.lower() in {".md", ".markdown"}:
            docs.append(load_markdown_file(file_path, root=p))
        else:
            docs.append(load_text_file(file_path, root=p))
    return docs


def corpus_to_hybrid_docs(docs: list[Document]) -> list[str]:
    """Return plain text strings suitable for :func:`hybrid_search`."""
    return [d.text for d in docs]


def save_corpus_jsonl(docs: list[Document], path: str | Path) -> None:
    """Write documents as one JSON object per line (UTF-8)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(json.dumps(asdict(doc), ensure_ascii=False))
            fh.write("\n")


def load_corpus_jsonl(path: str | Path) -> list[Document]:
    """Load a JSONL corpus previously written by :func:`save_corpus_jsonl`."""
    docs: list[Document] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid JSON on line {line_no} of {path}: {exc}"
                ) from exc
            if not isinstance(obj, dict):
                raise ValueError(
                    f"expected object on line {line_no} of {path}, got {type(obj).__name__}"
                )
            docs.append(
                Document(
                    id=str(obj.get("id", "")),
                    path=str(obj.get("path", "")),
                    text=str(obj.get("text", "")),
                    meta=dict(obj.get("meta") or {}),
                )
            )
    return docs
