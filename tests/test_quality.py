"""Unit tests for ragpractices.quality (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.quality import (  # noqa: E402
    chunk_stats,
    dedupe_near,
    flag_chunks,
)


class TestChunkStats(unittest.TestCase):
    def test_stats(self) -> None:
        texts = ["abcd", "", "hello world", "x"]
        s = chunk_stats(texts, very_short=3)
        self.assertEqual(s.n, 4)
        self.assertEqual(s.empty_count, 1)
        self.assertEqual(s.very_short_count, 1)  # "x"
        self.assertEqual(s.min_length, 0)
        self.assertEqual(s.max_length, len("hello world"))
        self.assertGreater(s.mean_length, 0)

    def test_empty_corpus(self) -> None:
        s = chunk_stats([])
        self.assertEqual(s.n, 0)
        self.assertEqual(s.mean_length, 0.0)


class TestFlagChunks(unittest.TestCase):
    def test_flags(self) -> None:
        texts = ["", "short", "y" * 50, "z" * 5000]
        issues = flag_chunks(texts, min_chars=10, max_chars=100)
        kinds = {i.kind for i in issues}
        self.assertIn("empty", kinds)
        self.assertIn("too_short", kinds)
        self.assertIn("too_long", kinds)
        # "y"*50 is fine
        self.assertEqual(len([i for i in issues if i.index == 2]), 0)


class TestDedupeNear(unittest.TestCase):
    def test_drops_near_dupes(self) -> None:
        texts = [
            "Refund requests within thirty days of purchase include order id",
            "Refund requests within thirty days of purchase include order id!",
            "Completely different password reset expiry content here",
        ]
        result = dedupe_near(texts, threshold=0.8)
        self.assertIn(0, result.kept_indices)
        self.assertIn(2, result.kept_indices)
        self.assertNotIn(1, result.kept_indices)
        self.assertEqual(len(result.dropped_pairs), 1)
        kept, dropped, sim = result.dropped_pairs[0]
        self.assertEqual(kept, 0)
        self.assertEqual(dropped, 1)
        self.assertGreaterEqual(sim, 0.8)

    def test_threshold_bounds(self) -> None:
        with self.assertRaises(ValueError):
            dedupe_near(["a"], threshold=1.5)


if __name__ == "__main__":
    unittest.main()
