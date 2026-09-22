"""Unit tests for ragpractices.pipeline (stdlib unittest)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.pipeline import (  # noqa: E402
    load_pipeline_config,
    result_to_dict,
    run_pipeline,
)


class TestLoadPipelineConfig(unittest.TestCase):
    def test_loads_and_rejects_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "p.json"
            path.write_text(
                json.dumps({"stages": [{"name": "hybrid", "params": {"top": 2}}]}),
                encoding="utf-8",
            )
            cfg = load_pipeline_config(path)
            self.assertEqual(len(cfg["stages"]), 1)

            bad = Path(tmp) / "bad.json"
            bad.write_text(
                json.dumps({"stages": [{"name": "explode"}]}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_pipeline_config(bad)


class TestRunPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.docs = [
            {"id": "doc-0", "text": "Refund requests are accepted within 30 days of purchase."},
            {"id": "doc-1", "text": "Standard shipping takes 5-7 business days."},
            {"id": "doc-2", "text": "Password reset links expire after 15 minutes."},
        ]
        self.config = {
            "answer": "Refunds are accepted within 30 days of purchase.",
            "stages": [
                {"name": "rewrite", "params": {"mode": "expand"}},
                {"name": "hybrid", "params": {"fusion": "rrf", "top": 3}},
                {"name": "rerank", "params": {"top_k": 2}},
                {"name": "pack", "params": {"max_tokens": 100}},
                {"name": "ground", "params": {}},
                {"name": "cite", "params": {"style": "numeric"}},
                {"name": "decide", "params": {"min_top_score": 0.0, "min_groundedness": 0.0}},
            ],
        }

    def test_runs_all_stages_with_traces(self) -> None:
        result = run_pipeline(self.config, query="refund policy", docs=self.docs)
        self.assertTrue(result.ok)
        names = [s.name for s in result.stages]
        self.assertEqual(
            names,
            ["rewrite", "hybrid", "rerank", "pack", "ground", "cite", "decide"],
        )
        for s in result.stages:
            self.assertTrue(s.ok)
            self.assertGreaterEqual(s.ms, 0.0)
        self.assertIsNotNone(result.final.get("decision"))
        payload = result_to_dict(result)
        self.assertEqual(payload["query"], "refund policy")
        self.assertTrue(payload["ok"])

    def test_empty_query_raises(self) -> None:
        with self.assertRaises(ValueError):
            run_pipeline(self.config, query="  ", docs=self.docs)


if __name__ == "__main__":
    unittest.main()
