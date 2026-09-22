"""Unit tests for ragpractices.rubric (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.rubric import (  # noqa: E402
    DIMENSIONS,
    MAX_TOTAL,
    format_scorecard,
    score_answer,
)


def _full(**overrides: int) -> dict[str, int]:
    base = {d: 2 for d in DIMENSIONS}
    base.update(overrides)
    return base


class TestScoreAnswer(unittest.TestCase):
    def test_perfect_pass(self) -> None:
        result = score_answer(_full())
        self.assertTrue(result["passed"])
        self.assertEqual(result["total"], MAX_TOTAL)
        self.assertEqual(result["max"], MAX_TOTAL)
        self.assertEqual(result["gate_failures"], [])

    def test_groundedness_gate_fail(self) -> None:
        result = score_answer(_full(groundedness=0))
        self.assertFalse(result["passed"])
        self.assertTrue(any("groundedness" in f for f in result["gate_failures"]))

    def test_groundedness_one_passes_gate(self) -> None:
        result = score_answer(_full(groundedness=1, relevance=0))
        self.assertTrue(result["passed"])
        self.assertEqual(result["total"], 1 + 0 + 2 + 2)

    def test_missing_dimension(self) -> None:
        with self.assertRaises(ValueError):
            score_answer({"groundedness": 2})

    def test_unknown_dimension(self) -> None:
        scores = _full()
        scores["fluency"] = 2
        with self.assertRaises(ValueError):
            score_answer(scores)

    def test_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            score_answer(_full(relevance=3))
        with self.assertRaises(ValueError):
            score_answer(_full(relevance=-1))


class TestFormatScorecard(unittest.TestCase):
    def test_contains_status(self) -> None:
        card = format_scorecard(score_answer(_full()))
        self.assertIn("PASS", card)
        self.assertIn("groundedness: 2/2", card)
        self.assertIn(f"total: {MAX_TOTAL}/{MAX_TOTAL}", card)

    def test_fail_lists_gate(self) -> None:
        card = format_scorecard(score_answer(_full(groundedness=0)))
        self.assertIn("FAIL", card)
        self.assertIn("gate failures", card)


if __name__ == "__main__":
    unittest.main()
