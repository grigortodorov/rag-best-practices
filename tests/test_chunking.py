"""Unit tests for ragpractices.chunking (stdlib unittest)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Allow `python -m unittest` without an editable install.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.chunking import chunk_by_headings, chunk_text  # noqa: E402


class TestChunkText(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("   \n"), [])

    def test_short_text_single_chunk(self) -> None:
        text = "hello world"
        self.assertEqual(chunk_text(text, chunk_size=100, overlap=10), [text])

    def test_overlap_windows(self) -> None:
        text = "abcdefghijklmnopqrstuvwxyz"  # 26 chars
        chunks = chunk_text(text, chunk_size=10, overlap=2)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0], "abcdefghij")
        self.assertEqual(chunks[1], "ijklmnopqr")
        # Last chunk reaches the end
        self.assertTrue(text.endswith(chunks[-1][-5:]))
        joined_span = "".join(
            c if i == 0 else c[2:] for i, c in enumerate(chunks)
        )
        self.assertEqual(joined_span, text)

    def test_invalid_args(self) -> None:
        with self.assertRaises(ValueError):
            chunk_text("x", chunk_size=0)
        with self.assertRaises(ValueError):
            chunk_text("x", chunk_size=10, overlap=10)
        with self.assertRaises(ValueError):
            chunk_text("x", chunk_size=10, overlap=-1)


class TestChunkByHeadings(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertEqual(chunk_by_headings(""), [])

    def test_preamble_and_sections(self) -> None:
        md = (
            "Intro paragraph.\n\n"
            "# Title One\n"
            "Body one.\n\n"
            "## Title Two\n"
            "Body two.\n"
        )
        chunks = chunk_by_headings(md, max_chars=1200)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0]["heading"], "")
        self.assertIn("Intro", chunks[0]["text"])
        self.assertEqual(chunks[1]["heading"], "Title One")
        self.assertIn("Body one", chunks[1]["text"])
        self.assertEqual(chunks[2]["heading"], "Title Two")
        self.assertIn("Body two", chunks[2]["text"])

    def test_splits_long_section(self) -> None:
        body = "x" * 250
        md = f"# Long\n{body}"
        chunks = chunk_by_headings(md, max_chars=100)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertEqual(c["heading"], "Long")
            self.assertLessEqual(len(c["text"]), 100)

    def test_no_headings(self) -> None:
        md = "Just a paragraph with no headings."
        chunks = chunk_by_headings(md)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["heading"], "")
        self.assertEqual(chunks[0]["text"], md)

    def test_invalid_max_chars(self) -> None:
        with self.assertRaises(ValueError):
            chunk_by_headings("x", max_chars=0)


if __name__ == "__main__":
    unittest.main()
