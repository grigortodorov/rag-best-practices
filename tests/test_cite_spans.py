"""Unit tests for ragpractices.cite_spans (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.cite_spans import (  # noqa: E402
    extract_citation_indices,
    extract_quotes,
    format_cite_span_report,
    report_to_dict,
    verify_citation_spans,
)


class TestExtract(unittest.TestCase):
    def test_quotes_and_markers(self) -> None:
        text = 'See "30 days of purchase" [1] and 【2】.'
        quotes = extract_quotes(text)
        self.assertIn("30 days of purchase", quotes)
        indices = extract_citation_indices(text)
        self.assertEqual(indices, [1, 2])


class TestVerifyCitationSpans(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = [
            {
                "id": "doc-0",
                "text": "Refund requests are accepted within 30 days of purchase.",
            },
            {
                "id": "doc-1",
                "text": "Standard shipping takes 5-7 business days.",
            },
        ]

    def test_good_and_hallucinated_quote(self) -> None:
        answer = (
            'Customers get a refund within "30 days of purchase" [1]. '
            'Also "flying unicorns grant refunds" [2].'
        )
        report = verify_citation_spans(answer, self.sources)
        self.assertEqual(report.n_quotes, 2)
        self.assertEqual(report.n_supported, 1)
        self.assertEqual(len(report.unsupported_quotes), 1)
        self.assertEqual(report.unsupported_quotes[0].quote, "flying unicorns grant refunds")
        self.assertEqual(report.supported_quotes[0].matched_source_id, "doc-0")
        self.assertFalse(report.all_supported)
        text = format_cite_span_report(report)
        self.assertIn("unsupported", text)
        payload = report_to_dict(report)
        self.assertEqual(payload["n_supported"], 1)

    def test_whitespace_normalized_match(self) -> None:
        answer = 'Policy says "30   days   of   purchase".'
        report = verify_citation_spans(answer, self.sources)
        self.assertEqual(report.n_supported, 1)

    def test_orphan_citation(self) -> None:
        answer = "Claim with no source [9]."
        report = verify_citation_spans(answer, self.sources)
        self.assertIn(9, report.orphan_citations)
        self.assertFalse(report.all_supported)

    def test_unused_sources(self) -> None:
        answer = 'Only "30 days of purchase" [1].'
        report = verify_citation_spans(answer, self.sources)
        self.assertIn("doc-1", report.unused_sources)

    def test_all_good(self) -> None:
        answer = 'Refund within "30 days of purchase" [1].'
        report = verify_citation_spans(answer, self.sources)
        self.assertTrue(report.all_supported)
        self.assertEqual(report.orphan_citations, [])


if __name__ == "__main__":
    unittest.main()
