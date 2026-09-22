"""Metadata / tag / tenant / ACL document filters (stdlib only).

Fail-closed ACL: if a document has an ``acl`` list and the caller's
``roles`` do not intersect it, the document is dropped. Tenant mismatches
are also dropped when filtering by tenant.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(x) for x in value]
    return [str(value)]


def _normalize_doc(item: Any, *, index: int = 0) -> dict[str, Any]:
    if isinstance(item, str):
        return {"id": f"doc-{index}", "text": item}
    if isinstance(item, dict):
        row = dict(item)
        if "id" not in row:
            row["id"] = f"doc-{index}"
        if "text" not in row and "document" in row:
            row["text"] = row["document"]
        return row
    raise TypeError(f"doc {index} must be str or dict")


def filter_docs(
    docs: Sequence[dict[str, Any] | str],
    *,
    tags: Sequence[str] | None = None,
    tenant: str | None = None,
    roles: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter documents by optional tags, tenant, and ACL roles.

    Document fields (all optional except that filtered results keep the
    original keys): ``id``, ``text``, ``tags``, ``tenant``, ``acl``
    (list of roles/users allowed to see the doc).

    Rules (fail-closed):

    - If ``tags`` is set, keep docs whose ``tags`` intersect the requested
      tags (docs with no tags are dropped when filtering by tags).
    - If ``tenant`` is set, drop docs that have a different non-empty
      ``tenant``. Docs with no tenant are kept (unknown ≠ mismatch).
    - If ``roles`` is provided and a doc has a non-empty ``acl``, keep only
      when the role sets intersect (empty roles → drop ACL-protected docs).
      If ``roles`` is omitted, ACL is not checked. Docs without ``acl`` are
      not ACL-restricted.

    Args:
        docs: Documents as dicts (or plain strings treated as text-only).
        tags: Required tag intersection (optional).
        tenant: Required tenant match when the doc declares a tenant.
        roles: Caller roles / users for ACL checks.

    Returns:
        Filtered list of document dicts (normalized with ``id``).
    """
    want_tags = {t.casefold() for t in _as_list(tags)} if tags is not None else None
    want_roles = {r.casefold() for r in _as_list(roles)} if roles is not None else None
    tenant_cf = tenant.casefold() if isinstance(tenant, str) and tenant else None

    out: list[dict[str, Any]] = []
    for i, raw in enumerate(docs):
        doc = _normalize_doc(raw, index=i)

        # Tags
        if want_tags is not None:
            doc_tags = {t.casefold() for t in _as_list(doc.get("tags"))}
            if not doc_tags or not (doc_tags & want_tags):
                continue

        # Tenant
        if tenant_cf is not None:
            doc_tenant = doc.get("tenant")
            if doc_tenant is not None and str(doc_tenant).strip():
                if str(doc_tenant).casefold() != tenant_cf:
                    continue

        # ACL fail-closed (only when caller supplies roles)
        if want_roles is not None:
            acl_raw = doc.get("acl")
            if acl_raw is not None:
                acl = {a.casefold() for a in _as_list(acl_raw)}
                if acl and not (acl & want_roles):
                    continue

        out.append(doc)
    return out


def load_docs_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Load document dicts from a JSONL file (one object per line)."""
    docs: list[dict[str, Any]] = []
    text = Path(path).read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError(f"JSONL line {i + 1} must be an object")
        docs.append(_normalize_doc(obj, index=i))
    return docs
