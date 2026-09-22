"""Command-line entry point: ``ragpractices``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from ragpractices import __version__
from ragpractices.checklist import get_checklist
from ragpractices.chunking import chunk_by_headings, chunk_text
from ragpractices.rubric import DIMENSIONS, format_scorecard, score_answer


def _parse_scores(spec: str) -> dict[str, int]:
    """Parse ``groundedness=2,relevance=1,...`` into a score dict."""
    scores: dict[str, int] = {}
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"expected name=value, got {part!r}")
        name, raw = part.split("=", 1)
        name = name.strip()
        try:
            scores[name] = int(raw.strip())
        except ValueError as exc:
            raise ValueError(f"invalid score for {name!r}: {raw!r}") from exc
    return scores


def _prompt_scores() -> dict[str, int]:
    print("Enter scores 0/1/2 for each dimension:", file=sys.stderr)
    scores: dict[str, int] = {}
    for dim in DIMENSIONS:
        while True:
            raw = input(f"  {dim}: ").strip()
            try:
                value = int(raw)
            except ValueError:
                print("    please enter an integer 0, 1, or 2", file=sys.stderr)
                continue
            if value not in (0, 1, 2):
                print("    please enter 0, 1, or 2", file=sys.stderr)
                continue
            scores[dim] = value
            break
    return scores


def cmd_chunk(args: argparse.Namespace) -> int:
    path = Path(args.path)
    text = path.read_text(encoding="utf-8")
    if args.by_headings:
        chunks = chunk_by_headings(text, max_chars=args.max_chars)
    else:
        pieces = chunk_text(text, chunk_size=args.chunk_size, overlap=args.overlap)
        chunks = [{"text": p, "heading": ""} for p in pieces]
    json.dump(chunks, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    if args.scores:
        scores = _parse_scores(args.scores)
    else:
        scores = _prompt_scores()
    result = score_answer(scores)
    sys.stdout.write(format_scorecard(result))
    return 0 if result["passed"] else 1


def cmd_checklist(_args: argparse.Namespace) -> int:
    sys.stdout.write(get_checklist())
    if not get_checklist().endswith("\n"):
        sys.stdout.write("\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ragpractices",
        description="Toolkit helpers for RAG chunking, scoring, and checklists.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_chunk = sub.add_parser("chunk", help="Chunk a text or Markdown file to JSON")
    p_chunk.add_argument("path", help="Path to a UTF-8 text/Markdown file")
    p_chunk.add_argument(
        "--chunk-size",
        type=int,
        default=800,
        help="Max characters per window (default: 800)",
    )
    p_chunk.add_argument(
        "--overlap",
        type=int,
        default=100,
        help="Overlap between windows (default: 100)",
    )
    p_chunk.add_argument(
        "--by-headings",
        action="store_true",
        help="Split on Markdown ATX headings first",
    )
    p_chunk.add_argument(
        "--max-chars",
        type=int,
        default=1200,
        help="Max chars per heading section chunk (default: 1200)",
    )
    p_chunk.set_defaults(func=cmd_chunk)

    p_score = sub.add_parser(
        "score",
        help="Score an answer with the groundedness/relevance rubric",
    )
    p_score.add_argument(
        "--scores",
        metavar="SPEC",
        help=(
            "Comma-separated scores, e.g. "
            "groundedness=2,relevance=1,completeness=2,citation_quality=1"
        ),
    )
    p_score.set_defaults(func=cmd_score)

    p_check = sub.add_parser(
        "checklist",
        help="Print a short RAG principles checklist",
    )
    p_check.set_defaults(func=cmd_checklist)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return int(args.func(args))
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
