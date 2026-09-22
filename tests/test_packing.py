"""Unit tests for ragpractices.packing (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.packing import (  # noqa: E402
    PackResult,
    estimate_tokens,
    pack_context,
    truncate_to_tokens,
)


class TestEstimateTokens(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("   "), 0)

    def test_four_chars_one_token(self) -> None:
        self.assertEqual(estimate_tokens("abcd"), 1)
        self.assertEqual(estimate_tokens("abcde"), 2)
        self.assertEqual(estimate_tokens("a" * 8), 2)


class TestTruncateToTokens(unittest.TestCase):
    def test_no_op_when_short(self) -> None:
        self.assertEqual(truncate_to_tokens("hello", 10), "hello")

    def test_hard_cap(self) -> None:
        text = "abcdefghijklmnopqrstuvwxyz"
        out = truncate_to_tokens(text, 2)
        self.assertEqual(len(out), 8)
        self.assertLessEqual(estimate_tokens(out), 2)

    def test_zero_and_negative(self) -> None:
        self.assertEqual(truncate_to_tokens("abc", 0), "")
        with self.assertRaises(ValueError):
            truncate_to_tokens("abc", -1)


class TestPackContext(unittest.TestCase):
    def test_greedy_under_budget(self) -> None:
        docs = ["aaaa", "bbbb", "cccc"]  # 1 token each
        result = pack_context(docs, max_tokens=3, separator="")
        self.assertIsInstance(result, PackResult)
        self.assertEqual(result.included, [0, 1, 2])
        self.assertEqual(result.omitted, [])
        self.assertEqual(result.packed_text, "aaaabbbbcccc")
        self.assertEqual(result.max_tokens, 3)

    def test_skips_oversized_without_truncate(self) -> None:
        docs = ["a" * 40, "bbbb", "cccc"]  # first ~10 tokens
        result = pack_context(docs, max_tokens=5, separator="")
        self.assertEqual(result.included, [1, 2])
        self.assertEqual(result.omitted, [0])
        self.assertIn("bbbb", result.packed_text)

    def test_truncate_last(self) -> None:
        docs = ["aaaa", "b" * 40]
        result = pack_context(docs, max_tokens=4, separator="", truncate=True)
        self.assertEqual(result.included, [0, 1])
        self.assertTrue(result.packed_text.startswith("aaaa"))
        self.assertLessEqual(result.estimated_tokens, 4)

    def test_dict_ids_and_score_order(self) -> None:
        docs = [
            {"id": "low", "text": "xxxx", "score": 0.1},
            {"id": "high", "text": "yyyy", "score": 0.9},
        ]
        result = pack_context(
            docs, max_tokens=2, separator="", preserve_order=False
        )
        self.assertEqual(result.included[0], "high")

    def test_empty_corpus(self) -> None:
        result = pack_context([], max_tokens=10)
        self.assertEqual(result.packed_text, "")
        self.assertEqual(result.included, [])
        self.assertEqual(result.estimated_tokens, 0)

    def test_negative_budget(self) -> None:
        with self.assertRaises(ValueError):
            pack_context(["a"], max_tokens=-1)

    def test_document_alias(self) -> None:
        result = pack_context(
            [{"id": "d0", "document": "hello world"}],
            max_tokens=10,
            separator="",
        )
        self.assertEqual(result.included, ["d0"])
        self.assertIn("hello", result.packed_text)


if __name__ == "__main__":
    unittest.main()
