"""Unit tests for ragpractices.compare (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.compare import (  # noqa: E402
    STRATEGY_NAMES,
    compare_strategies,
    format_compare_table,
    report_to_dict,
)
from ragpractices.eval import GoldenCase  # noqa: E402


class TestCompareStrategies(unittest.TestCase):
    def setUp(self) -> None:
        self.docs = [
            "Refund requests are accepted within 30 days of purchase.",
            "Standard shipping takes 5-7 business days.",
            "Password reset links expire after 15 minutes.",
        ]
        self.cases = [
            GoldenCase(query="refund 30 days", expected_ids=["doc-0"], id="r"),
            GoldenCase(query="shipping business days", expected_ids=["doc-1"], id="s"),
        ]

    def test_runs_all_strategies(self) -> None:
        report = compare_strategies(self.cases, self.docs, k=2)
        self.assertEqual(report.n_cases, 2)
        self.assertEqual(report.k, 2)
        names = [s.name for s in report.strategies]
        self.assertEqual(names, list(STRATEGY_NAMES))
        self.assertEqual(set(report.ranking), set(STRATEGY_NAMES))
        for s in report.strategies:
            self.assertGreaterEqual(s.hit_at_k_rate, 0.0)
            self.assertLessEqual(s.hit_at_k_rate, 1.0)
        table = format_compare_table(report)
        self.assertIn("keyword", table)
        self.assertIn("hybrid_rerank", table)
        self.assertIn("ranking:", table)
        payload = report_to_dict(report)
        self.assertEqual(payload["n_cases"], 2)
        self.assertEqual(len(payload["strategies"]), 4)

    def test_unknown_strategy(self) -> None:
        with self.assertRaises(ValueError):
            compare_strategies(self.cases, self.docs, strategies=["nope"])

    def test_dict_docs(self) -> None:
        docs = [{"id": "a", "text": self.docs[0]}, {"id": "b", "text": self.docs[1]}]
        cases = [GoldenCase(query="refund", expected_ids=["a"], id="c")]
        report = compare_strategies(cases, docs, k=1, strategies=["keyword", "hybrid"])
        self.assertEqual(len(report.strategies), 2)
        self.assertGreaterEqual(report.strategies[0].hit_at_k_rate, 0.0)


if __name__ == "__main__":
    unittest.main()
