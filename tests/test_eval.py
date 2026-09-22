"""Unit tests for ragpractices.eval (stdlib unittest)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.eval import (  # noqa: E402
    GoldenCase,
    evaluate_retrieval,
    hit_at_k,
    load_golden_jsonl,
    mrr,
    report_to_dict,
)


class TestHitAtK(unittest.TestCase):
    def test_hit_and_miss(self) -> None:
        self.assertTrue(hit_at_k(["a", "b", "c"], ["b"], k=2))
        self.assertFalse(hit_at_k(["a", "b", "c"], ["b"], k=1))
        self.assertFalse(hit_at_k(["a", "b"], ["z"], k=5))
        self.assertFalse(hit_at_k(["a"], [], k=1))

    def test_k_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            hit_at_k(["a"], ["a"], k=0)


class TestMRR(unittest.TestCase):
    def test_ranks(self) -> None:
        self.assertAlmostEqual(mrr(["a", "b", "c"], ["b"]), 0.5)
        self.assertAlmostEqual(mrr(["target", "x"], ["target"]), 1.0)
        self.assertEqual(mrr(["a", "b"], ["z"]), 0.0)
        self.assertEqual(mrr([], ["a"]), 0.0)
        self.assertEqual(mrr(["a"], []), 0.0)


class TestEvaluateRetrieval(unittest.TestCase):
    def test_aggregate(self) -> None:
        cases = [
            GoldenCase(query="q1", expected_ids=["doc-0"], id="c1"),
            GoldenCase(query="q2", expected_ids=["doc-9"], id="c2"),
        ]

        def retrieve(q: str) -> list[str]:
            if q == "q1":
                return ["doc-0", "doc-1"]
            return ["doc-1", "doc-2"]

        report = evaluate_retrieval(cases, retrieve, k=1)
        self.assertEqual(report.n_cases, 2)
        self.assertAlmostEqual(report.hit_at_k_rate, 0.5)
        self.assertAlmostEqual(report.mean_mrr, 0.5)
        self.assertEqual(report.k, 1)
        self.assertTrue(report.cases[0].hit_at_k)
        self.assertFalse(report.cases[1].hit_at_k)
        payload = report_to_dict(report)
        self.assertEqual(payload["n_cases"], 2)
        self.assertIn("notes", payload)


class TestLoadGolden(unittest.TestCase):
    def test_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "g.jsonl"
            path.write_text(
                json.dumps({"query": "refund", "expected_ids": ["doc-0"]}) + "\n",
                encoding="utf-8",
            )
            cases = load_golden_jsonl(path)
            self.assertEqual(len(cases), 1)
            self.assertEqual(cases[0].query, "refund")
            self.assertEqual(cases[0].expected_ids, ["doc-0"])


if __name__ == "__main__":
    unittest.main()
