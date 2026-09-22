#!/usr/bin/env python3
"""End-to-end ragpractices demo (stdlib only).

Chain: load sample docs → optional rewrite → hybrid_search → rerank →
pack_context → attach_citations → check_groundedness on a canned answer.

Run from the repository root:

    PYTHONPATH=src python examples/e2e_demo.py
    # or after pip install -e .
    python examples/e2e_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.cli import run_demo_pipeline  # noqa: E402


def main() -> int:
    docs = _ROOT / "examples" / "hybrid-docs.txt"
    if not docs.is_file():
        docs = _ROOT / "examples" / "ingest-sample"
    if not docs.exists():
        print(f"error: sample docs not found under {_ROOT / 'examples'}", file=sys.stderr)
        return 2
    return run_demo_pipeline(
        "refund shipping policy",
        docs,
        max_tokens=200,
        rewrite=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
