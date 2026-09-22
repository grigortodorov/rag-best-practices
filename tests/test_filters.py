"""Unit tests for ragpractices.filters (stdlib unittest)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ragpractices.filters import filter_docs, load_docs_jsonl  # noqa: E402


DOCS = [
    {
        "id": "public-refund",
        "text": "refund 30 days",
        "tags": ["refund", "policy"],
        "tenant": "acme",
        "acl": ["public", "support"],
    },
    {
        "id": "internal-pw",
        "text": "password reset",
        "tags": ["password"],
        "tenant": "acme",
        "acl": ["support", "security"],
    },
    {
        "id": "other-tenant",
        "text": "other refund",
        "tags": ["refund"],
        "tenant": "beta",
        "acl": ["public"],
    },
    {
        "id": "no-acl",
        "text": "open doc",
        "tags": ["misc"],
        "tenant": "acme",
    },
]


class TestFilterDocs(unittest.TestCase):
    def test_tags(self) -> None:
        out = filter_docs(DOCS, tags=["refund"])
        ids = [d["id"] for d in out]
        self.assertIn("public-refund", ids)
        self.assertIn("other-tenant", ids)
        self.assertNotIn("internal-pw", ids)

    def test_tenant(self) -> None:
        out = filter_docs(DOCS, tenant="acme")
        ids = [d["id"] for d in out]
        self.assertNotIn("other-tenant", ids)
        self.assertIn("public-refund", ids)

    def test_acl_fail_closed(self) -> None:
        # roles omitted → ACL not checked
        out = filter_docs(DOCS)
        ids = [d["id"] for d in out]
        self.assertIn("public-refund", ids)
        self.assertIn("internal-pw", ids)
        self.assertIn("no-acl", ids)

        # empty roles → fail closed on ACL docs
        out_empty = filter_docs(DOCS, roles=[])
        ids_empty = [d["id"] for d in out_empty]
        self.assertNotIn("public-refund", ids_empty)
        self.assertNotIn("internal-pw", ids_empty)
        self.assertIn("no-acl", ids_empty)

        out2 = filter_docs(DOCS, roles=["public"])
        ids2 = [d["id"] for d in out2]
        self.assertIn("public-refund", ids2)
        self.assertNotIn("internal-pw", ids2)
        self.assertIn("no-acl", ids2)

        out3 = filter_docs(DOCS, roles=["support"])
        ids3 = [d["id"] for d in out3]
        self.assertIn("public-refund", ids3)
        self.assertIn("internal-pw", ids3)

    def test_combined(self) -> None:
        out = filter_docs(DOCS, tags=["refund"], tenant="acme", roles=["public"])
        self.assertEqual([d["id"] for d in out], ["public-refund"])


class TestLoadDocsJsonl(unittest.TestCase):
    def test_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "d.jsonl"
            path.write_text(json.dumps(DOCS[0]) + "\n", encoding="utf-8")
            docs = load_docs_jsonl(path)
            self.assertEqual(docs[0]["id"], "public-refund")


if __name__ == "__main__":
    unittest.main()
