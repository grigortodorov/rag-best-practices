"""Unit tests for ragpractices.abstain (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.abstain import should_answer  # noqa: E402


class TestShouldAnswer(unittest.TestCase):
    def test_empty_retrieval(self) -> None:
        r = should_answer(empty_retrieval=True, top_score=0.9, groundedness=0.9)
        self.assertEqual(r.decision, "abstain")
        self.assertIn("empty", r.reason.lower())

    def test_low_top_score(self) -> None:
        r = should_answer(top_score=0.05, min_top_score=0.1)
        self.assertEqual(r.decision, "abstain")

    def test_low_groundedness_clarify(self) -> None:
        r = should_answer(top_score=0.5, groundedness=0.1, min_groundedness=0.3)
        self.assertEqual(r.decision, "clarify")

    def test_answer_ok(self) -> None:
        r = should_answer(top_score=0.5, groundedness=0.8)
        self.assertEqual(r.decision, "answer")

    def test_unchecked_scores_allow_answer(self) -> None:
        r = should_answer()
        self.assertEqual(r.decision, "answer")


if __name__ == "__main__":
    unittest.main()
