"""Unit tests for ragpractices.html_ingest (stdlib unittest)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.html_ingest import html_to_text, load_html_file  # noqa: E402
from ragpractices.ingest import content_hash, load_path  # noqa: E402


SAMPLE = """<!DOCTYPE html>
<html><head><title>FAQ</title><style>x{}</style><script>1</script></head>
<body><h1>Hello</h1><p>Refunds within <b>30 days</b>.</p>
<ul><li>Item A</li><li>Item B</li></ul></body></html>"""


class TestHtmlToText(unittest.TestCase):
    def test_strips_script_style_and_keeps_text(self) -> None:
        text = html_to_text(SAMPLE)
        self.assertIn("Hello", text)
        self.assertIn("Refunds within 30 days", text)
        self.assertIn("Item A", text)
        self.assertNotIn("script", text.casefold())
        self.assertNotIn("x{}", text)

    def test_empty(self) -> None:
        self.assertEqual(html_to_text(""), "")


class TestContentHash(unittest.TestCase):
    def test_stable(self) -> None:
        a = content_hash("hello")
        b = content_hash("hello")
        c = content_hash("hello!")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(a), 64)


class TestLoadHtmlFile(unittest.TestCase):
    def test_loads_with_hash_and_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "faq.html"
            path.write_text(SAMPLE, encoding="utf-8")
            doc = load_html_file(path)
            self.assertEqual(doc.id, "faq")
            self.assertIn("Refunds", doc.text)
            self.assertEqual(doc.meta.get("content_type"), "html")
            self.assertEqual(doc.meta.get("title"), "FAQ")
            self.assertEqual(doc.meta.get("content_hash"), content_hash(doc.text))

    def test_load_path_picks_up_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.html").write_text("<p>Alpha</p>", encoding="utf-8")
            (root / "b.txt").write_text("Beta", encoding="utf-8")
            docs = load_path(root)
            by_id = {d.id: d for d in docs}
            self.assertIn("a.html", by_id)
            self.assertIn("Alpha", by_id["a.html"].text)
            self.assertIn("content_hash", by_id["a.html"].meta)
            self.assertIn("content_hash", by_id["b.txt"].meta)


if __name__ == "__main__":
    unittest.main()
