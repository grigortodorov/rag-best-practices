"""Unit tests for ragpractices.claim_check (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.claim_check import (  # noqa: E402
    check_claims,
    extract_sensitive_tokens,
    format_claim_check_report,
    report_to_dict,
    split_claims,
)


class TestSplitClaims(unittest.TestCase):
    def test_splits_sentences(self) -> None:
        claims = split_claims(
            "Refunds are within 30 days of purchase. Shipping takes five business days."
        )
        self.assertEqual(len(claims), 2)
        self.assertIn("Refunds", claims[0])
        self.assertIn("Shipping", claims[1])

    def test_drops_short_fragments(self) -> None:
        # "Ok." has <3 content words
        claims = split_claims("Ok. Refunds are within thirty days of purchase.")
        self.assertEqual(len(claims), 1)
        self.assertIn("Refunds", claims[0])

    def test_empty(self) -> None:
        self.assertEqual(split_claims(""), [])
        self.assertEqual(split_claims("   "), [])


class TestExtractSensitiveTokens(unittest.TestCase):
    def test_numbers_dates_ids(self) -> None:
        text = (
            "Order INV-1042 for 1,200 units (15%) shipped on 2024-01-15 "
            "or Jan 15, 2024; see #99887 and ticket ABC1234."
        )
        tokens = extract_sensitive_tokens(text)
        kinds = {t: k for t, k in tokens}
        self.assertEqual(kinds.get("INV-1042"), "id")
        self.assertEqual(kinds.get("ABC1234"), "id")
        self.assertEqual(kinds.get("#99887"), "id")
        self.assertEqual(kinds.get("1,200"), "number")
        self.assertEqual(kinds.get("15%"), "number")
        self.assertEqual(kinds.get("2024-01-15"), "date")
        self.assertIn(("Jan 15, 2024", "date"), tokens)

    def test_skips_lone_year_as_number(self) -> None:
        tokens = extract_sensitive_tokens("Policy updated in 2024.")
        kinds = [k for _t, k in tokens]
        # bare 2024 should not appear as number
        self.assertNotIn(("2024", "number"), tokens)
        self.assertEqual(kinds.count("number"), 0)


class TestCheckClaims(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = [
            {
                "id": "doc-0",
                "text": (
                    "Refund requests are accepted within 30 days of purchase. "
                    "Include your order ID when contacting support."
                ),
            },
            {
                "id": "doc-1",
                "text": (
                    "Standard shipping takes 5-7 business days. "
                    "Express shipping arrives in 2 business days."
                ),
            },
        ]

    def test_fully_supported_pass(self) -> None:
        answer = (
            "Refund requests are accepted within 30 days of purchase. "
            "Standard shipping takes 5-7 business days."
        )
        report = check_claims(answer, self.sources)
        self.assertEqual(report.decision, "pass")
        self.assertTrue(all(c.status == "supported" for c in report.claims))
        self.assertEqual(report.n_unsupported, 0)
        self.assertEqual(report.n_missing_entities, 0)
        text = format_claim_check_report(report)
        self.assertIn("decision: pass", text)
        payload = report_to_dict(report)
        self.assertEqual(payload["decision"], "pass")

    def test_hallucinated_claim_abstain(self) -> None:
        answer = (
            "Flying unicorns grant unlimited refunds forever without receipts."
        )
        report = check_claims(answer, self.sources)
        self.assertEqual(report.decision, "abstain")
        self.assertGreaterEqual(report.n_unsupported, 1)
        self.assertTrue(any(c.status == "unsupported" for c in report.claims))

    def test_invented_number_abstain(self) -> None:
        # Words overlap with refund policy, but invented number 99 is not in sources
        answer = (
            "Refund requests are accepted within 99 days of purchase."
        )
        report = check_claims(answer, self.sources)
        self.assertEqual(report.decision, "abstain")
        self.assertGreaterEqual(report.n_missing_entities, 1)
        missing = [e for e in report.entities if not e.found_in_sources]
        self.assertTrue(any(e.token == "99" for e in missing))

    def test_weak_overlap_rewrite(self) -> None:
        # Partial lexical overlap without hard entity fails → rewrite
        answer = (
            "Customers may request purchase refunds under the accepted policy window."
        )
        report = check_claims(
            answer,
            self.sources,
            supported_threshold=0.90,
            weak_threshold=0.20,
        )
        self.assertEqual(report.n_unsupported, 0)
        self.assertEqual(report.n_missing_entities, 0)
        self.assertGreaterEqual(report.n_weak, 1)
        self.assertEqual(report.decision, "rewrite")

    def test_empty_answer_abstain(self) -> None:
        report = check_claims("", self.sources)
        self.assertEqual(report.decision, "abstain")
        self.assertIn("empty answer", report.reasons)

    def test_number_present_in_sources_ok(self) -> None:
        answer = "Refund requests are accepted within 30 days of purchase."
        report = check_claims(answer, self.sources)
        # 30 appears in sources
        thirties = [e for e in report.entities if e.token == "30"]
        self.assertTrue(thirties)
        self.assertTrue(all(e.found_in_sources for e in thirties))
        self.assertEqual(report.decision, "pass")


if __name__ == "__main__":
    unittest.main()
