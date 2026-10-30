"""CLI contract tests for claim-check output."""

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

from ragpractices.cli import main


class TestClaimCheckCli(unittest.TestCase):
    def setUp(self) -> None:
        self.answer = "Refund requests are accepted within 30 days of purchase."
        self.sources = [
            {
                "id": "policy",
                "text": "Refund requests are accepted within 30 days of purchase.",
            }
        ]

    def run_claim_check(self, *extra_args: str) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            sources_path = Path(tmp) / "sources.json"
            sources_path.write_text(json.dumps(self.sources), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "claim-check",
                        "--answer",
                        self.answer,
                        "--sources",
                        str(sources_path),
                        *extra_args,
                    ]
                )
        return exit_code, output.getvalue()

    def test_json_flag_emits_machine_readable_claim_report(self) -> None:
        exit_code, stdout = self.run_claim_check("--json")

        report = json.loads(stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["decision"], "pass")
        self.assertEqual(report["reasons"], ["all claims supported; no missing entities"])
        self.assertEqual(report["claims"][0]["status"], "supported")
        self.assertEqual(report["entities"][0]["token"], "30")
        self.assertTrue(report["entities"][0]["found_in_sources"])

    def test_human_readable_output_remains_the_default(self) -> None:
        exit_code, stdout = self.run_claim_check()

        self.assertEqual(exit_code, 0)
        self.assertTrue(stdout.startswith("decision: pass\n"))
        self.assertIn("claims: 1 supported, 0 weak, 0 unsupported", stdout)
        with self.assertRaises(json.JSONDecodeError):
            json.loads(stdout)


if __name__ == "__main__":
    unittest.main()
