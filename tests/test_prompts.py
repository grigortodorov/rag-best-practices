"""Unit tests for ragpractices.prompts (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.prompts import build_clarify_prompt, build_grounded_prompt  # noqa: E402


class TestBuildGroundedPrompt(unittest.TestCase):
    def test_cite_style(self) -> None:
        prompt = build_grounded_prompt(
            "What is the refund window?",
            ["Refunds within 30 days.", "Shipping takes 5 days."],
            style="cite",
        )
        self.assertIn("ONLY the provided context", prompt)
        self.assertIn("[1]", prompt)
        self.assertIn("[2]", prompt)
        self.assertIn("What is the refund window?", prompt)
        self.assertIn("### System", prompt)

    def test_abstain_style(self) -> None:
        prompt = build_grounded_prompt(
            "Who is the CEO?",
            [{"id": "x", "text": "Refunds within 30 days."}],
            style="abstain",
        )
        self.assertIn("ABSTAIN", prompt)
        self.assertIn("[1]", prompt)

    def test_empty_question(self) -> None:
        with self.assertRaises(ValueError):
            build_grounded_prompt("  ", ["ctx"])

    def test_invalid_style(self) -> None:
        with self.assertRaises(ValueError):
            build_grounded_prompt("q", ["c"], style="nope")

    def test_max_context_chars(self) -> None:
        long_ctx = "word " * 500
        prompt = build_grounded_prompt("q", [long_ctx], max_context_chars=80)
        self.assertLessEqual(len(prompt), 500)


class TestBuildClarifyPrompt(unittest.TestCase):
    def test_with_hints(self) -> None:
        prompt = build_clarify_prompt("refund?", missing_hints=["order id", "date"])
        self.assertIn("clarifying", prompt.lower())
        self.assertIn("order id", prompt)
        self.assertIn("date", prompt)
        self.assertIn("refund?", prompt)

    def test_no_hints(self) -> None:
        prompt = build_clarify_prompt("help me")
        self.assertIn("help me", prompt)
        self.assertNotIn("### Missing", prompt)


if __name__ == "__main__":
    unittest.main()
