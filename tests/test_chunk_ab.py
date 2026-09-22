"""Unit tests for ragpractices.chunk_ab (stdlib unittest)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.chunk_ab import (  # noqa: E402
    STRATEGY_NAMES,
    apply_strategy,
    compare_chunkers,
    format_chunk_ab_table,
    load_sources,
    report_to_dict,
)
from ragpractices.eval import GoldenCase  # noqa: E402


class TestApplyStrategy(unittest.TestCase):
    def test_stable_chunk_ids(self) -> None:
        sources = [{"id": "a", "text": "Hello world. " * 40}, {"id": "b", "text": "# Title\nBody text here."}]
        chunks = apply_strategy("fixed_small", sources)
        self.assertTrue(all(c.chunk_id.startswith(c.doc_id + ":") for c in chunks))
        self.assertGreater(len(chunks), 1)
        ids = [c.chunk_id for c in chunks]
        self.assertEqual(len(ids), len(set(ids)))

    def test_headings_strategy(self) -> None:
        sources = [{"id": "md", "text": "# One\nAlpha beta.\n# Two\nGamma delta."}]
        chunks = apply_strategy("headings", sources)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertTrue(chunks[0].chunk_id.startswith("md:"))

    def test_unknown_strategy(self) -> None:
        with self.assertRaises(ValueError):
            apply_strategy("nope", [{"id": "x", "text": "hi"}])


class TestCompareChunkers(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = [
            {"id": "refund", "text": "Refund requests are accepted within 30 days of purchase."},
            {"id": "ship", "text": "Standard shipping takes 5-7 business days."},
            {"id": "pw", "text": "Password reset links expire after 15 minutes."},
        ]
        self.cases = [
            GoldenCase(query="refund 30 days", expected_ids=["refund"], id="r"),
            GoldenCase(query="shipping business days", expected_ids=["ship"], id="s"),
        ]

    def test_all_strategies(self) -> None:
        report = compare_chunkers(self.sources, self.cases, k=2)
        self.assertEqual(report.n_cases, 2)
        self.assertEqual(report.n_sources, 3)
        names = [s.name for s in report.strategies]
        self.assertEqual(names, list(STRATEGY_NAMES))
        self.assertEqual(set(report.ranking), set(STRATEGY_NAMES))
        for s in report.strategies:
            self.assertGreaterEqual(s.hit_at_k_rate, 0.0)
            self.assertLessEqual(s.hit_at_k_rate, 1.0)
            self.assertGreater(s.n_chunks, 0)
        table = format_chunk_ab_table(report)
        self.assertIn("fixed", table)
        self.assertIn("ranking:", table)
        payload = report_to_dict(report)
        self.assertEqual(payload["n_cases"], 2)

    def test_document_level_hit(self) -> None:
        # expected is source doc id; chunk ids are refund:0 etc.
        report = compare_chunkers(
            self.sources, self.cases, k=1, strategies=["fixed"]
        )
        self.assertEqual(len(report.strategies), 1)
        self.assertGreaterEqual(report.strategies[0].hit_at_k_rate, 0.5)

    def test_string_sources(self) -> None:
        sources = [s["text"] for s in self.sources]
        cases = [
            GoldenCase(query="refund", expected_ids=["doc-0"], id="c"),
        ]
        report = compare_chunkers(sources, cases, k=1, strategies=["fixed_large"])
        self.assertEqual(report.n_sources, 3)
        self.assertGreaterEqual(report.strategies[0].hit_at_k_rate, 0.0)

    def test_unknown_strategy_compare(self) -> None:
        with self.assertRaises(ValueError):
            compare_chunkers(self.sources, self.cases, strategies=["nope"])

    def test_load_sources_dir(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sample = root / "examples" / "ingest-sample"
        if sample.is_dir():
            loaded = load_sources(sample)
            self.assertGreaterEqual(len(loaded), 3)
            ids = {s["id"] for s in loaded}
            self.assertTrue(any("refund" in i or i.endswith(".txt") for i in ids))


class TestLoadSourcesHybrid(unittest.TestCase):
    def test_hybrid_docs(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("Alpha refund policy.\n---\nBeta shipping info.\n")
            path = fh.name
        try:
            loaded = load_sources(path)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0]["id"], "doc-0")
        finally:
            Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
