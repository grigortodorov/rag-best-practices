"""Unit tests for ragpractices.groundedness (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.groundedness import (  # noqa: E402
    GroundednessReport,
    check_groundedness,
)


class TestCheckGroundedness(unittest.TestCase):
    def test_fully_supported(self) -> None:
        answer = "Refunds are accepted within 30 days of purchase."
        sources = [
            "Refund requests are accepted within 30 days of purchase.",
        ]
        report = check_groundedness(answer, sources)
        self.assertIsInstance(report, GroundednessReport)
        self.assertGreaterEqual(report.score, 0.7)
        self.assertEqual(report.supported_word_ratio, report.score)
        self.assertIn("heuristic", report.notes.lower())

    def test_unsupported_hallucination(self) -> None:
        answer = "We offer lifetime free unicorn shipping worldwide tomorrow."
        sources = [
            "Refund requests are accepted within 30 days of purchase.",
        ]
        report = check_groundedness(answer, sources)
        self.assertLess(report.score, 0.4)
        self.assertTrue(len(report.unsupported_sentences) >= 1)

    def test_per_source_scores(self) -> None:
        answer = "Refund within 30 days. Shipping takes 5 days."
        sources = [
            {"id": "refund", "text": "Refund within 30 days of purchase."},
            {"id": "ship", "document": "Shipping takes 5-7 business days."},
        ]
        report = check_groundedness(answer, sources)
        self.assertEqual(len(report.per_source), 2)
        ids = {row["id"] for row in report.per_source}
        self.assertEqual(ids, {"refund", "ship"})
        for row in report.per_source:
            self.assertIn("overlap", row)
            self.assertGreaterEqual(row["overlap"], 0.0)

    def test_empty_answer(self) -> None:
        report = check_groundedness("", ["some source text here"])
        self.assertEqual(report.score, 1.0)
        self.assertEqual(report.unsupported_sentences, [])

    def test_min_overlap_note(self) -> None:
        report = check_groundedness(
            "Completely unrelated zebra giraffe.",
            ["Refund policy within thirty days."],
            min_overlap=0.5,
        )
        self.assertLess(report.score, 0.5)
        self.assertIn("min_overlap", report.notes)

    def test_score_bounds(self) -> None:
        report = check_groundedness("hello world", ["hello world again"])
        self.assertGreaterEqual(report.score, 0.0)
        self.assertLessEqual(report.score, 1.0)

    def test_invalid_min_overlap(self) -> None:
        with self.assertRaises(ValueError):
            check_groundedness("a", ["b"], min_overlap=1.5)


if __name__ == "__main__":
    unittest.main()
