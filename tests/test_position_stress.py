"""Unit tests for ragpractices.position_stress (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.position_stress import (  # noqa: E402
    format_position_stress_report,
    report_to_dict,
    run_position_stress,
)


class TestPositionStress(unittest.TestCase):
    def setUp(self) -> None:
        self.gold = "Refund requests are accepted within 30 days of purchase."
        self.fillers = [
            "Standard shipping takes 5-7 business days in most regions.",
            "Password reset links expire after 15 minutes for security.",
            "Our privacy policy explains how account data is stored.",
            "International orders may incur customs duties paid by recipient.",
        ]

    def test_three_positions(self) -> None:
        report = run_position_stress(self.gold, self.fillers, max_tokens=256)
        self.assertEqual(len(report.positions), 3)
        names = [p.position for p in report.positions]
        self.assertEqual(names, ["first", "middle", "last"])
        risks = {p.position: p.attention_risk for p in report.positions}
        self.assertEqual(risks["middle"], "high")
        self.assertEqual(risks["first"], "low")
        self.assertEqual(risks["last"], "medium")
        for p in report.positions:
            self.assertTrue(p.gold_present)
            self.assertGreaterEqual(p.gold_offset, 0)
            self.assertGreater(p.estimate_tokens, 0)
        # Offsets differ by position
        offsets = [p.gold_offset for p in report.positions]
        self.assertEqual(offsets[0], 0)
        self.assertGreater(offsets[1], offsets[0])
        self.assertGreater(offsets[2], offsets[1])
        table = format_position_stress_report(report)
        self.assertIn("middle", table)
        payload = report_to_dict(report)
        self.assertEqual(len(payload["positions"]), 3)

    def test_dict_fillers(self) -> None:
        fillers = [{"id": "a", "text": t} for t in self.fillers]
        report = run_position_stress(self.gold, fillers, max_tokens=128)
        self.assertEqual(len(report.positions), 3)

    def test_empty_gold_raises(self) -> None:
        with self.assertRaises(ValueError):
            run_position_stress("  ", self.fillers)

    def test_max_tokens_raises(self) -> None:
        with self.assertRaises(ValueError):
            run_position_stress(self.gold, self.fillers, max_tokens=0)

    def test_no_fillers(self) -> None:
        report = run_position_stress(self.gold, [], max_tokens=64)
        for p in report.positions:
            self.assertTrue(p.gold_present)


if __name__ == "__main__":
    unittest.main()
