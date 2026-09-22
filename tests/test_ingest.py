"""Unit tests for ragpractices.ingest (stdlib unittest)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.ingest import (  # noqa: E402
    Document,
    corpus_to_hybrid_docs,
    load_corpus_jsonl,
    load_markdown_file,
    load_path,
    load_text_file,
    save_corpus_jsonl,
)


class TestLoadTextFile(unittest.TestCase):
    def test_loads_utf8_and_id_from_stem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.txt"
            path.write_text("hello world\n", encoding="utf-8")
            doc = load_text_file(path)
            self.assertIsInstance(doc, Document)
            self.assertEqual(doc.id, "notes")
            self.assertEqual(doc.text, "hello world\n")
            self.assertEqual(doc.meta, {})
            self.assertEqual(doc.path, str(path))


class TestLoadMarkdownFile(unittest.TestCase):
    def test_strips_yaml_front_matter_into_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.md"
            path.write_text(
                "---\ntitle: Hello\npriority: 2\npublished: true\n---\n\n# Body\n\nContent.\n",
                encoding="utf-8",
            )
            doc = load_markdown_file(path)
            self.assertEqual(doc.id, "doc")
            self.assertEqual(doc.meta.get("title"), "Hello")
            self.assertEqual(doc.meta.get("priority"), 2)
            self.assertIs(doc.meta.get("published"), True)
            self.assertTrue(doc.text.lstrip().startswith("# Body"))
            self.assertNotIn("---", doc.text.splitlines()[0] if doc.text else "")

    def test_no_front_matter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plain.md"
            path.write_text("# Title\n\nNo front matter.\n", encoding="utf-8")
            doc = load_markdown_file(path)
            self.assertEqual(doc.meta, {})
            self.assertIn("# Title", doc.text)


class TestLoadPath(unittest.TestCase):
    def test_directory_loads_txt_and_md_skips_hidden_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("alpha", encoding="utf-8")
            (root / "b.md").write_text(
                "---\ntag: x\n---\n\nbeta body\n", encoding="utf-8"
            )
            (root / ".secret.txt").write_text("hidden", encoding="utf-8")
            venv = root / ".venv" / "lib"
            venv.mkdir(parents=True)
            (venv / "skip.txt").write_text("skipme", encoding="utf-8")
            nested = root / "sub"
            nested.mkdir()
            (nested / "c.txt").write_text("gamma", encoding="utf-8")

            docs = load_path(root)
            ids = sorted(d.id for d in docs)
            self.assertEqual(ids, ["a.txt", "b.md", "sub/c.txt"])
            by_id = {d.id: d for d in docs}
            self.assertEqual(by_id["a.txt"].text, "alpha")
            self.assertEqual(by_id["b.md"].meta.get("tag"), "x")
            self.assertIn("beta body", by_id["b.md"].text)
            self.assertEqual(by_id["sub/c.txt"].text, "gamma")

    def test_single_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "solo.txt"
            path.write_text("solo", encoding="utf-8")
            docs = load_path(path)
            self.assertEqual(len(docs), 1)
            self.assertEqual(docs[0].text, "solo")

    def test_custom_glob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "keep.txt").write_text("k", encoding="utf-8")
            (root / "drop.md").write_text("d", encoding="utf-8")
            docs = load_path(root, glob="**/*.txt")
            self.assertEqual([d.id for d in docs], ["keep.txt"])

    def test_missing_path_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_path("/nonexistent/path/for/ingest/tests")


class TestCorpusJsonlAndHybrid(unittest.TestCase):
    def test_roundtrip_and_hybrid_texts(self) -> None:
        docs = [
            Document(id="a", path="a.txt", text="one", meta={"k": 1}),
            Document(id="b", path="b.md", text="two", meta={}),
        ]
        self.assertEqual(corpus_to_hybrid_docs(docs), ["one", "two"])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "corpus.jsonl"
            save_corpus_jsonl(docs, out)
            lines = out.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            first = json.loads(lines[0])
            self.assertEqual(first["id"], "a")
            self.assertEqual(first["meta"], {"k": 1})
            loaded = load_corpus_jsonl(out)
            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0].id, "a")
            self.assertEqual(loaded[0].text, "one")
            self.assertEqual(loaded[0].meta, {"k": 1})
            self.assertEqual(loaded[1].text, "two")


if __name__ == "__main__":
    unittest.main()
