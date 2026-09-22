"""Unit tests for ragpractices.citations (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.citations import (  # noqa: E402
    Citation,
    attach_citations,
    build_sources_block,
    format_inline_citations,
)


class TestCitation(unittest.TestCase):
    def test_from_dict_fallbacks(self) -> None:
        c = Citation.from_dict(
            {"index": 3, "document": "hello world", "score": 0.9},
            fallback_index=0,
        )
        self.assertEqual(c.id, "3")
        self.assertEqual(c.snippet, "hello world")
        self.assertEqual(c.score, 0.9)


class TestFormatInline(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = [
            {"id": "refund-policy", "title": "Refunds", "snippet": "30 days"},
            {"id": "shipping", "title": "Shipping", "snippet": "5-7 days"},
        ]

    def test_numeric_replaces_brackets(self) -> None:
        ans = "You can get a refund [1] and shipping takes a week [2]."
        out = format_inline_citations(ans, self.sources, style="numeric")
        self.assertIn("(1)", out)
        self.assertIn("(2)", out)
        self.assertNotIn("[1]", out)

    def test_numeric_appends_when_missing(self) -> None:
        out = format_inline_citations("Refunds are available.", self.sources, style="numeric")
        self.assertTrue(out.endswith("(1) (2)"))

    def test_bracketed_at_and_append(self) -> None:
        out = format_inline_citations(
            "See details [@refund-policy].",
            self.sources,
            style="bracketed",
        )
        self.assertIn("[refund-policy]", out)
        self.assertNotIn("[@", out)

        out2 = format_inline_citations("Hello.", self.sources, style="bracketed")
        self.assertIn("[refund-policy]", out2)
        self.assertIn("[shipping]", out2)


class TestSourcesBlock(unittest.TestCase):
    def test_numeric_and_bracketed(self) -> None:
        sources = [
            {"id": "a", "title": "A", "snippet": "alpha"},
            {"id": "b", "text": "bravo text"},
        ]
        num = build_sources_block(sources, style="numeric")
        self.assertIn("Sources:", num)
        self.assertIn("(1)", num)
        self.assertIn("(2)", num)

        br = build_sources_block(sources, style="bracketed")
        self.assertIn("[a]", br)
        self.assertIn("[b]", br)


class TestAttachCitations(unittest.TestCase):
    def test_full_payload(self) -> None:
        retrieved = [
            {"id": "doc-0", "document": "Refund within 30 days.", "score": 0.8},
            {"id": "doc-1", "text": "Shipping 5-7 days.", "score": 0.5},
        ]
        result = attach_citations(
            "Refunds are within 30 days [1].",
            retrieved,
            style="numeric",
        )
        self.assertIn("answer", result)
        self.assertIn("sources_block", result)
        self.assertIn("full_text", result)
        self.assertIn("(1)", result["answer"])
        self.assertIn("Sources:", result["sources_block"])
        self.assertIn(result["answer"], result["full_text"])
        self.assertIn(result["sources_block"], result["full_text"])


if __name__ == "__main__":
    unittest.main()
