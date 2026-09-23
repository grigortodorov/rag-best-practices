"""Unit tests for ragpractices.conflict_check (stdlib unittest)."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.cli import main  # noqa: E402
from ragpractices.conflict_check import (  # noqa: E402
    check_conflicts,
    extract_number_mentions,
    find_negation_conflicts,
    find_number_conflicts,
    format_conflict_report,
    report_to_dict,
)


class TestExtractNumberMentions(unittest.TestCase):
    def test_extracts_from_dicts_and_strings(self) -> None:
        sources = [
            {"id": "a", "text": "Refund within 30 days."},
            "Also see 15% discount.",
        ]
        mentions = extract_number_mentions(sources)
        values = {(m.source_id, m.value) for m in mentions}
        self.assertIn(("a", "30"), values)
        self.assertIn(("doc-1", "15"), values)
        self.assertTrue(any(m.raw == "15%" for m in mentions))


class TestNumberConflicts(unittest.TestCase):
    def test_thirty_vs_ninety_days(self) -> None:
        sources = [
            {
                "id": "policy-a",
                "text": "Refund requests are accepted within 30 days of purchase.",
            },
            {
                "id": "policy-b",
                "text": "Refund requests are accepted within 90 days of purchase.",
            },
        ]
        report = check_conflicts(sources)
        self.assertEqual(report.decision, "conflict")
        self.assertEqual(report.n_sources, 2)
        self.assertTrue(any(c.kind == "number" for c in report.conflicts))
        text = format_conflict_report(report)
        self.assertIn("decision: conflict", text)
        self.assertIn("30", text)
        self.assertIn("90", text)
        payload = report_to_dict(report)
        self.assertEqual(payload["decision"], "conflict")

    def test_agreeing_docs_ok(self) -> None:
        sources = [
            {"id": "a", "text": "Refund within 30 days of purchase."},
            {"id": "b", "text": "Customers may request a refund within 30 days."},
        ]
        report = check_conflicts(sources)
        self.assertEqual(report.decision, "ok")
        self.assertEqual(report.conflicts, [])
        mentions = extract_number_mentions(sources)
        self.assertEqual(find_number_conflicts(mentions), [])


class TestNegationConflicts(unittest.TestCase):
    def test_returns_accepted_vs_not(self) -> None:
        sources = [
            {"id": "a", "text": "Returns are accepted for unopened items."},
            {"id": "b", "text": "Returns are not accepted for unopened items."},
        ]
        report = check_conflicts(sources)
        self.assertEqual(report.decision, "conflict")
        self.assertTrue(any(c.kind == "negation" for c in report.conflicts))
        negs = find_negation_conflicts(sources)
        self.assertGreaterEqual(len(negs), 1)


class TestAnswerSide(unittest.TestCase):
    def test_answer_preferring_one_side_still_conflict(self) -> None:
        sources = [
            {"id": "a", "text": "Refund window is 30 days from purchase."},
            {"id": "b", "text": "Refund window is 90 days from purchase."},
        ]
        report = check_conflicts(
            sources, answer="You can get a refund within 30 days."
        )
        self.assertEqual(report.decision, "conflict")
        summaries = " ".join(c.summary for c in report.conflicts)
        self.assertIn("Answer", summaries)
        self.assertTrue(any("answer" in c.source_ids for c in report.conflicts))


class TestEmptySources(unittest.TestCase):
    def test_empty_ok_with_reason(self) -> None:
        report = check_conflicts([])
        self.assertEqual(report.decision, "ok")
        self.assertEqual(report.n_sources, 0)
        self.assertIn("no sources to compare", report.reasons)


class TestCliConflictCheck(unittest.TestCase):
    def test_cli_conflict_exit_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "docs.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "id": "a",
                        "text": "Refund requests are accepted within 30 days.",
                    }
                )
                + "\n"
                + json.dumps(
                    {
                        "id": "b",
                        "text": "Refund requests are accepted within 90 days.",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["conflict-check", "--sources", str(path)])
            self.assertEqual(code, 1)
            self.assertIn("decision: conflict", buf.getvalue())

    def test_cli_ok_exit_0(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "docs.jsonl"
            path.write_text(
                json.dumps({"id": "a", "text": "Refund within 30 days."})
                + "\n"
                + json.dumps({"id": "b", "text": "Refund within 30 days."})
                + "\n",
                encoding="utf-8",
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = main(["conflict-check", "--sources", str(path)])
            self.assertEqual(code, 0)
            self.assertIn("decision: ok", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
