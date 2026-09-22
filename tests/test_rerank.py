"""Unit tests for ragpractices.rerank (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.rerank import mmr_rerank, rerank  # noqa: E402


class TestRerank(unittest.TestCase):
    def setUp(self) -> None:
        self.docs = [
            "Refund requests within 30 days with order ID.",
            "Standard shipping takes 5-7 business days.",
            "Password reset links expire after 15 minutes.",
            "Privacy policy for account data storage.",
        ]

    def test_prefers_keyword_overlap(self) -> None:
        results = rerank("refund", self.docs)
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0]["index"], 0)
        for r in results:
            self.assertIn("index", r)
            self.assertIn("score", r)
            self.assertIn("document", r)
            self.assertEqual(r["document"], self.docs[r["index"]])

    def test_top_k(self) -> None:
        results = rerank("refund shipping", self.docs, top_k=2)
        self.assertEqual(len(results), 2)

    def test_blend_with_incoming_scores(self) -> None:
        # Strong prior on password doc should lift it when blended
        scores = [0.0, 0.0, 1.0, 0.0]
        results = rerank("zzzz", self.docs, scores=scores)
        # Keyword overlap all ~0; incoming prefers index 2
        self.assertEqual(results[0]["index"], 2)

    def test_scores_length_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            rerank("x", self.docs, scores=[0.1, 0.2])

    def test_empty(self) -> None:
        self.assertEqual(rerank("x", []), [])


class TestMmrRerank(unittest.TestCase):
    def setUp(self) -> None:
        self.docs = [
            "Refund policy allows returns within 30 days.",
            "Refund requests need an order ID for returns.",
            "Shipping takes 5-7 business days for delivery.",
            "Password authentication and login reset links.",
        ]

    def test_diversity_vs_duplicates(self) -> None:
        # First two are near-duplicates on refund; MMR should diversify.
        results = mmr_rerank("refund shipping", self.docs, lambda_mult=0.5, top_k=3)
        self.assertEqual(len(results), 3)
        indices = [r["index"] for r in results]
        # Should not pick both near-duplicate refund docs as the only hits
        # before including shipping when lambda is moderate.
        self.assertIn(2, indices)  # shipping doc gets a slot

    def test_lambda_bounds(self) -> None:
        with self.assertRaises(ValueError):
            mmr_rerank("x", self.docs, lambda_mult=1.5)

    def test_deterministic(self) -> None:
        a = mmr_rerank("refund", self.docs, top_k=2)
        b = mmr_rerank("refund", self.docs, top_k=2)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
