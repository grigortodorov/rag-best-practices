"""Unit tests for ragpractices.canaries (stdlib unittest)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.canaries import (  # noqa: E402
    Canary,
    format_canary_report,
    load_canaries_jsonl,
    report_to_dict,
    run_canaries,
)


class TestRunCanaries(unittest.TestCase):
    def setUp(self) -> None:
        self.docs = [
            {"id": "refund", "text": "Refund requests are accepted within 30 days of purchase."},
            {"id": "ship", "text": "Standard shipping takes 5-7 business days."},
            {"id": "pw", "text": "Password reset links expire after 15 minutes."},
        ]
        self.canaries = [
            Canary(query="refund 30 days", expected_ids=["refund"], id="c1"),
            Canary(query="shipping business days", expected_ids=["ship"], id="c2"),
        ]

    def test_all_pass(self) -> None:
        report = run_canaries(self.canaries, self.docs, k=2)
        self.assertTrue(report.all_passed)
        self.assertEqual(report.n_passed, 2)
        self.assertEqual(report.n_failed, 0)
        text = format_canary_report(report)
        self.assertIn("PASS", text)
        payload = report_to_dict(report)
        self.assertTrue(payload["all_passed"])

    def test_fail_wrong_expected(self) -> None:
        bad = [Canary(query="refund 30 days", expected_ids=["missing"], id="bad")]
        report = run_canaries(bad, self.docs, k=2)
        self.assertFalse(report.all_passed)
        self.assertEqual(report.n_failed, 1)
        self.assertIn("FAIL", format_canary_report(report))

    def test_keyword_mode(self) -> None:
        report = run_canaries(self.canaries, self.docs, k=2, retrieve="keyword")
        self.assertEqual(report.n_canaries, 2)

    def test_acl_filter(self) -> None:
        docs = [
            {
                "id": "pub",
                "text": "Refund requests are accepted within 30 days.",
                "tags": ["refund"],
                "tenant": "acme",
                "acl": ["public"],
            },
            {
                "id": "secret",
                "text": "Refund secret internal only window is 7 days.",
                "tags": ["refund"],
                "tenant": "acme",
                "acl": ["admin"],
            },
        ]
        cans = [
            Canary(
                query="refund days",
                expected_ids=["pub"],
                id="acl",
                tags=["refund"],
                tenant="acme",
                roles=["public"],
            )
        ]
        report = run_canaries(cans, docs, k=1)
        self.assertTrue(report.all_passed)
        self.assertEqual(report.results[0].filtered_n, 1)
        self.assertEqual(report.results[0].retrieved_ids, ["pub"])

    def test_unknown_retrieve(self) -> None:
        with self.assertRaises(ValueError):
            run_canaries(self.canaries, self.docs, retrieve="nope")

    def test_load_jsonl(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            fh.write(
                '{"id": "x", "query": "refund", "expected_ids": ["refund"]}\n'
            )
            path = fh.name
        try:
            cans = load_canaries_jsonl(path)
            self.assertEqual(len(cans), 1)
            self.assertEqual(cans[0].id, "x")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_example_fixtures(self) -> None:
        root = Path(__file__).resolve().parents[1]
        cans_path = root / "examples" / "canaries.jsonl"
        docs_path = root / "examples" / "acl-docs.jsonl"
        if cans_path.is_file() and docs_path.is_file():
            from ragpractices.filters import load_docs_jsonl

            cans = load_canaries_jsonl(cans_path)
            docs = load_docs_jsonl(docs_path)
            report = run_canaries(cans, docs, k=3)
            self.assertTrue(report.all_passed)
            self.assertGreaterEqual(report.n_canaries, 5)


if __name__ == "__main__":
    unittest.main()
