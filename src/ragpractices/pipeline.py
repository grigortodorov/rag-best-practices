"""Configurable RAG pipeline runner with stage traces (stdlib only).

Loads a small JSON config describing stages (rewrite, hybrid, rerank, pack,
ground, cite, decide) and runs them in order with ``time.perf_counter``
timings. Educational orchestration—not a production workflow engine.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ragpractices.abstain import should_answer
from ragpractices.filters import filter_docs
from ragpractices.citations import attach_citations
from ragpractices.groundedness import check_groundedness
from ragpractices.hybrid import hybrid_search
from ragpractices.packing import pack_context
from ragpractices.rerank import mmr_rerank, rerank
from ragpractices.rewrite import rewrite_query


KNOWN_STAGES = (
    "rewrite",
    "hybrid",
    "rerank",
    "pack",
    "ground",
    "cite",
    "decide",
)


@dataclass
class StageTrace:
    """Timing and summary for one pipeline stage."""

    name: str
    ms: float
    ok: bool
    summary: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class PipelineResult:
    """Outcome of ``run_pipeline``."""

    query: str
    stages: list[StageTrace] = field(default_factory=list)
    final: dict[str, Any] = field(default_factory=dict)
    ok: bool = True


def load_pipeline_config(path: str | Path) -> dict[str, Any]:
    """Load a pipeline JSON config from disk.

    Expected shape::

        {
          "stages": [
            {"name": "rewrite", "params": {"mode": "expand"}},
            {"name": "hybrid", "params": {"fusion": "rrf", "top": 5}},
            ...
          ],
          "answer": "optional canned answer for ground/cite"
        }
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("pipeline config must be a JSON object")
    stages = data.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("pipeline config needs a non-empty stages list")
    for i, stage in enumerate(stages):
        if not isinstance(stage, dict) or "name" not in stage:
            raise ValueError(f"stage {i} must be an object with a name")
        name = stage["name"]
        if name not in KNOWN_STAGES:
            raise ValueError(
                f"unknown stage {name!r}; known: {', '.join(KNOWN_STAGES)}"
            )
    return data


def _stage_params(stage: dict[str, Any]) -> dict[str, Any]:
    params = stage.get("params") or {}
    if not isinstance(params, dict):
        raise ValueError(f"stage {stage.get('name')!r} params must be an object")
    return params


def run_pipeline(
    config: dict[str, Any],
    *,
    query: str,
    docs: list[str] | list[dict[str, Any]],
) -> PipelineResult:
    """Execute configured stages in order; collect traces and a final payload.

    ``docs`` may be plain strings or dicts with ``id`` / ``text`` (or
    ``document``). Stages mutate an internal state (search query, ranked
    hits, packed text, decision, etc.).
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")

    # Normalize docs to id + text (+ optional metadata for filtering)
    raw_docs: list[dict[str, Any]] = []
    for i, item in enumerate(docs):
        if isinstance(item, str):
            raw_docs.append({"id": f"doc-{i}", "text": item})
        elif isinstance(item, dict):
            row = dict(item)
            if "text" not in row and "document" in row:
                row["text"] = row["document"]
            if "id" not in row:
                row["id"] = f"doc-{i}"
            raw_docs.append(row)
        else:
            raise TypeError(f"doc {i} must be str or dict")

    # Optional fail-closed metadata / ACL filter from config["filter"]
    filt = config.get("filter") or {}
    if isinstance(filt, dict) and filt:
        raw_docs = filter_docs(
            raw_docs,
            tags=filt.get("tags"),
            tenant=filt.get("tenant"),
            roles=filt.get("roles"),
        )

    texts = [str(d.get("text") or "") for d in raw_docs]
    ids = [str(d.get("id", f"doc-{i}")) for i, d in enumerate(raw_docs)]

    stages_cfg = config.get("stages") or []
    canned_answer = str(config.get("answer") or "")

    state: dict[str, Any] = {
        "query": query.strip(),
        "search_query": query.strip(),
        "texts": texts,
        "ids": ids,
        "hits": [],  # list of {index, score, document, id}
        "packed_text": "",
        "pack_included": [],
        "groundedness": None,
        "cited": None,
        "decision": None,
        "top_score": None,
    }

    traces: list[StageTrace] = []
    overall_ok = True

    for stage in stages_cfg:
        name = stage["name"]
        params = _stage_params(stage)
        t0 = time.perf_counter()
        try:
            summary = _run_stage(name, params, state, canned_answer=canned_answer)
            ms = (time.perf_counter() - t0) * 1000.0
            traces.append(StageTrace(name=name, ms=ms, ok=True, summary=summary))
        except Exception as exc:  # noqa: BLE001 — record and stop
            ms = (time.perf_counter() - t0) * 1000.0
            traces.append(
                StageTrace(
                    name=name,
                    ms=ms,
                    ok=False,
                    summary={},
                    error=str(exc),
                )
            )
            overall_ok = False
            break

    final = {
        "query": state["query"],
        "search_query": state["search_query"],
        "top_ids": [h["id"] for h in state["hits"][:5]],
        "top_score": state["top_score"],
        "packed_preview": (state["packed_text"] or "")[:200],
        "groundedness": state["groundedness"],
        "decision": state["decision"],
        "cited_preview": None,
    }
    if state["cited"]:
        full = state["cited"].get("full_text") or ""
        final["cited_preview"] = full[:200]

    return PipelineResult(
        query=state["query"],
        stages=traces,
        final=final,
        ok=overall_ok,
    )


def _run_stage(
    name: str,
    params: dict[str, Any],
    state: dict[str, Any],
    *,
    canned_answer: str,
) -> dict[str, Any]:
    if name == "rewrite":
        mode = str(params.get("mode", "expand"))
        rw = rewrite_query(state["query"], mode=mode)  # type: ignore[arg-type]
        state["search_query"] = rw["rewritten"]
        return {"mode": mode, "rewritten": rw["rewritten"]}

    if name == "hybrid":
        fusion = str(params.get("fusion", "rrf"))
        top = int(params.get("top", 5))
        rrf_k = int(params.get("rrf_k", 60))
        alpha = float(params.get("alpha", 0.5))
        results = hybrid_search(
            state["search_query"],
            state["texts"],
            fusion=fusion,  # type: ignore[arg-type]
            rrf_k=rrf_k,
            alpha=alpha,
        )
        if top > 0:
            results = results[:top]
        hits = []
        for r in results:
            hits.append(
                {
                    "index": r["index"],
                    "score": r["score"],
                    "document": r["document"],
                    "id": state["ids"][r["index"]],
                }
            )
        state["hits"] = hits
        state["top_score"] = hits[0]["score"] if hits else None
        return {
            "fusion": fusion,
            "n_hits": len(hits),
            "top_ids": [h["id"] for h in hits[:3]],
            "top_score": state["top_score"],
        }

    if name == "rerank":
        use_mmr = bool(params.get("mmr", False))
        top_k = int(params.get("top_k", params.get("top", 3)))
        lambda_mult = float(params.get("lambda_mult", 0.7))
        cand_docs = [h["document"] for h in state["hits"]]
        cand_meta = list(state["hits"])
        if not cand_docs:
            state["hits"] = []
            state["top_score"] = None
            return {"n_hits": 0, "mmr": use_mmr}
        if use_mmr:
            ranked = mmr_rerank(
                state["search_query"],
                cand_docs,
                lambda_mult=lambda_mult,
                top_k=top_k,
            )
        else:
            ranked = rerank(state["search_query"], cand_docs, top_k=top_k)
        new_hits = []
        for r in ranked:
            base = cand_meta[r["index"]]
            new_hits.append(
                {
                    "index": base["index"],
                    "score": r["score"],
                    "document": r["document"],
                    "id": base["id"],
                }
            )
        state["hits"] = new_hits
        state["top_score"] = new_hits[0]["score"] if new_hits else None
        return {
            "mmr": use_mmr,
            "n_hits": len(new_hits),
            "top_ids": [h["id"] for h in new_hits],
            "top_score": state["top_score"],
        }

    if name == "pack":
        max_tokens = int(params.get("max_tokens", 200))
        pack_docs = [
            {"id": h["id"], "text": h["document"], "score": h["score"]}
            for h in state["hits"]
        ]
        packed = pack_context(
            pack_docs,
            max_tokens=max_tokens,
            preserve_order=True,
        )
        state["packed_text"] = packed.packed_text
        state["pack_included"] = list(packed.included)
        return {
            "max_tokens": max_tokens,
            "included": packed.included,
            "omitted": packed.omitted,
            "estimated_tokens": packed.estimated_tokens,
        }

    if name == "ground":
        answer = str(params.get("answer") or canned_answer or state["packed_text"])
        sources = [
            {"id": h["id"], "text": h["document"]} for h in state["hits"]
        ]
        report = check_groundedness(answer, sources)
        state["groundedness"] = report.score
        state["_ground_answer"] = answer
        return {
            "score": report.score,
            "unsupported_count": len(report.unsupported_sentences),
        }

    if name == "cite":
        answer = str(
            params.get("answer")
            or canned_answer
            or state.get("_ground_answer")
            or state["packed_text"]
        )
        style = str(params.get("style", "numeric"))
        sources = [
            {"id": h["id"], "text": h["document"], "score": h["score"]}
            for h in state["hits"]
        ]
        cited = attach_citations(answer, sources, style=style)  # type: ignore[arg-type]
        state["cited"] = cited
        return {
            "style": style,
            "n_sources": len(sources),
            "preview": (cited.get("full_text") or "")[:120],
        }

    if name == "decide":
        min_top = float(params.get("min_top_score", 0.1))
        min_g = float(params.get("min_groundedness", 0.3))
        empty = len(state["hits"]) == 0
        result = should_answer(
            top_score=state["top_score"],
            groundedness=state["groundedness"],
            min_top_score=min_top,
            min_groundedness=min_g,
            empty_retrieval=empty,
        )
        state["decision"] = {
            "decision": result.decision,
            "reason": result.reason,
        }
        return dict(state["decision"])

    raise ValueError(f"unknown stage {name!r}")


def result_to_dict(result: PipelineResult) -> dict[str, Any]:
    """JSON-friendly serialization of :class:`PipelineResult`."""
    return {
        "query": result.query,
        "ok": result.ok,
        "final": result.final,
        "stages": [
            {
                "name": s.name,
                "ms": round(s.ms, 3),
                "ok": s.ok,
                "summary": s.summary,
                "error": s.error,
            }
            for s in result.stages
        ],
    }
