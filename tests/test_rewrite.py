"""Unit tests for ragpractices.rewrite (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.rewrite import multi_query, rewrite_query  # noqa: E402


class TestRewriteExpand(unittest.TestCase):
    def test_expands_refund_and_ship(self) -> None:
        result = rewrite_query("refund ship", mode="expand")
        self.assertEqual(result["mode"], "expand")
        self.assertEqual(result["original"], "refund ship")
        rewritten = result["rewritten"].casefold()
        self.assertIn("refund", rewritten)
        self.assertIn("return", rewritten)
        self.assertIn("ship", rewritten)
        self.assertIn("delivery", rewritten)
        self.assertIn("keywords", result)
        self.assertIn("refund", result["keywords"])

    def test_password_auth_expansion(self) -> None:
        result = rewrite_query("password reset", mode="expand")
        self.assertIn("auth", result["rewritten"].casefold())

    def test_invalid_mode(self) -> None:
        with self.assertRaises(ValueError):
            rewrite_query("x", mode="llm")


class TestRewriteClarify(unittest.TestCase):
    def test_short_gets_hint(self) -> None:
        result = rewrite_query("refund", mode="clarify")
        self.assertIn("looking for policy details", result["rewritten"])
        self.assertTrue(any("short" in n for n in result["notes"]))

    def test_long_stays_cleaned(self) -> None:
        q = "what is the refund window for digital goods"
        result = rewrite_query(q, mode="clarify")
        self.assertNotIn("looking for policy details", result["rewritten"])
        self.assertEqual(result["rewritten"], " ".join(q.split()))


class TestRewriteHyphenateSplit(unittest.TestCase):
    def test_camel_and_hyphen(self) -> None:
        result = rewrite_query("orderID password-reset", mode="hyphenate_split")
        tokens = result["rewritten"].casefold().split()
        self.assertIn("order", tokens)
        self.assertIn("id", tokens)
        self.assertIn("password", tokens)
        self.assertIn("reset", tokens)


class TestMultiQuery(unittest.TestCase):
    def test_returns_two_to_three_variants(self) -> None:
        variants = multi_query("refund ship")
        self.assertGreaterEqual(len(variants), 2)
        self.assertLessEqual(len(variants), 3)
        self.assertEqual(variants[0], "refund ship")
        # expand should add synonyms
        self.assertTrue(any("return" in v or "delivery" in v for v in variants))

    def test_deterministic(self) -> None:
        self.assertEqual(multi_query("refund ship"), multi_query("refund ship"))


if __name__ == "__main__":
    unittest.main()
