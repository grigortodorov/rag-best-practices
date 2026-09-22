"""Unit tests for ragpractices.hybrid (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.hybrid import (  # noqa: E402
    hybrid_search,
    keyword_score,
    normalize_scores,
    reciprocal_rank_fusion,
)


class TestKeywordScore(unittest.TestCase):
    def test_prefers_overlapping_docs(self) -> None:
        docs = [
            "cats and dogs are pets",
            "refund shipping policy for orders",
            "unrelated astronomy notes",
        ]
        scores = keyword_score("refund shipping", docs)
        self.assertEqual(len(scores), 3)
        self.assertGreater(scores[1], scores[0])
        self.assertGreater(scores[1], scores[2])

    def test_deterministic_and_empty(self) -> None:
        docs = ["Alpha Beta", "beta gamma"]
        a = keyword_score("Beta", docs)
        b = keyword_score("Beta", docs)
        self.assertEqual(a, b)
        self.assertEqual(keyword_score("x", []), [])


class TestNormalizeScores(unittest.TestCase):
    def test_minmax(self) -> None:
        self.assertEqual(normalize_scores([2.0, 4.0, 6.0]), [0.0, 0.5, 1.0])

    def test_empty_and_constant(self) -> None:
        self.assertEqual(normalize_scores([]), [])
        self.assertEqual(normalize_scores([3.0, 3.0, 3.0]), [0.0, 0.0, 0.0])


class TestReciprocalRankFusion(unittest.TestCase):
    def test_merges_lists(self) -> None:
        # Doc 0 best in first list, doc 1 best in second → both score; 2 trails.
        fused = reciprocal_rank_fusion([[0, 2, 1], [1, 0, 2]], k=60)
        indices = [i for i, _ in fused]
        self.assertEqual(set(indices), {0, 1, 2})
        # 0 and 1 should outrank 2 (each is rank-1 somewhere).
        self.assertLess(indices.index(0), indices.index(2))
        self.assertLess(indices.index(1), indices.index(2))
        scores = {i: s for i, s in fused}
        self.assertGreater(scores[0], scores[2])
        self.assertGreater(scores[1], scores[2])


class TestHybridSearch(unittest.TestCase):
    def setUp(self) -> None:
        self.docs = [
            "Refund requests within 30 days with order ID.",
            "Standard shipping takes 5-7 business days.",
            "Password reset links expire after 15 minutes.",
            "Privacy policy for account data storage.",
        ]

    def test_rrf_order_on_fixture(self) -> None:
        # Keyword "refund shipping" hits docs 0 and 1; dense prefers 1 then 3.
        dense = [0.1, 0.9, 0.0, 0.5]
        results = hybrid_search(
            "refund shipping",
            self.docs,
            dense,
            fusion="rrf",
        )
        self.assertEqual(len(results), 4)
        top_indices = [r["index"] for r in results]
        # Doc 1 appears in both strong sparse and dense → should be first.
        self.assertEqual(top_indices[0], 1)
        for r in results:
            self.assertIn("index", r)
            self.assertIn("score", r)
            self.assertIn("document", r)
            self.assertEqual(r["document"], self.docs[r["index"]])

    def test_weighted_alpha_extremes(self) -> None:
        dense = [0.0, 1.0, 0.0, 0.0]  # only doc 1 strong densely
        # alpha=1 → pure dense: doc 1 first
        dense_only = hybrid_search(
            "refund shipping",
            self.docs,
            dense,
            fusion="weighted",
            alpha=1.0,
        )
        self.assertEqual(dense_only[0]["index"], 1)

        # alpha=0 → pure sparse: refund/shipping docs (0 and/or 1) beat others
        sparse_only = hybrid_search(
            "refund shipping",
            self.docs,
            dense,
            fusion="weighted",
            alpha=0.0,
        )
        sparse_scores = keyword_score("refund shipping", self.docs)
        best_sparse = max(range(len(self.docs)), key=lambda i: sparse_scores[i])
        self.assertEqual(sparse_only[0]["index"], best_sparse)

    def test_none_dense_keyword_only(self) -> None:
        results = hybrid_search("refund", self.docs, None, fusion="rrf")
        self.assertEqual(results[0]["index"], 0)

    def test_dense_length_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            hybrid_search("x", self.docs, [0.1, 0.2])


if __name__ == "__main__":
    unittest.main()
