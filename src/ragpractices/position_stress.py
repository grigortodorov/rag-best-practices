"""Lost-in-the-middle position stress helpers (stdlib only).

Educational stub: packs gold evidence at ``first`` / ``middle`` / ``last``
among filler documents and reports token estimates, whether the gold
substring is present, its offset, and a simple attention-risk label
(middle = higher risk). Does **not** call an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Sequence

from ragpractices.packing import estimate_tokens, truncate_to_tokens

PositionName = Literal["first", "middle", "last"]
AttentionRisk = Literal["low", "medium", "high"]

_RISK: dict[PositionName, AttentionRisk] = {
    "first": "low",
    "middle": "high",
    "last": "medium",
}


@dataclass
class PositionResult:
    """One packed-context position probe."""

    position: PositionName
    packed_text: str
    estimate_tokens: int
    gold_present: bool
    gold_offset: int
    attention_risk: AttentionRisk
    n_fillers_used: int = 0


@dataclass
class PositionStressReport:
    """Lost-in-the-middle stress report across positions."""

    gold: str
    max_tokens: int
    positions: list[PositionResult] = field(default_factory=list)
    notes: str = (
        "Educational lost-in-the-middle stress stub (no LLM call). "
        "Middle position is labeled higher attention risk; verify with a "
        "real model eval before drawing product conclusions."
    )


def _as_texts(fillers: Sequence[str | dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for i, item in enumerate(fillers):
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            out.append(str(item.get("text") or item.get("document") or ""))
        else:
            raise TypeError(f"filler {i} must be str or dict")
    return [t for t in out if t.strip()]


def _pack_at_position(
    gold: str,
    fillers: list[str],
    position: PositionName,
    *,
    max_tokens: int,
) -> PositionResult:
    """Build a packed context with gold at the requested position."""
    # Place gold relative to fillers, then truncate to budget from the start
    # while ensuring we keep the gold segment when possible.
    if position == "first":
        ordered = [gold] + fillers
    elif position == "last":
        ordered = fillers + [gold]
    else:  # middle
        if not fillers:
            ordered = [gold]
        else:
            mid = len(fillers) // 2
            ordered = fillers[:mid] + [gold] + fillers[mid:]

    sep = "\n\n"
    # Greedy pack under max_tokens, preferring to include gold
    included: list[str] = []
    used = 0
    gold_included = False
    for piece in ordered:
        piece_tok = estimate_tokens(piece)
        extra = estimate_tokens(sep) if included else 0
        if used + extra + piece_tok > max_tokens and included:
            # If gold not yet in and this is gold, try force-fit truncated
            if piece == gold and not gold_included:
                remain = max(0, max_tokens - used - (estimate_tokens(sep) if included else 0))
                if remain > 0:
                    truncated = truncate_to_tokens(piece, remain)
                    if truncated.strip():
                        included.append(truncated)
                        gold_included = True
            break
        if included:
            used += estimate_tokens(sep)
        included.append(piece)
        used += piece_tok
        if piece == gold:
            gold_included = True

    packed = sep.join(included)
    # If nothing fit, hard-truncate gold alone
    if not packed.strip() and gold.strip():
        packed = truncate_to_tokens(gold, max_tokens)
        included = [packed] if packed.strip() else []
        gold_included = bool(packed.strip())

    # Offset of the inserted gold *segment* (not a coincidental substring in fillers)
    offset = -1
    present = False
    cursor = 0
    for i, piece in enumerate(included):
        if piece == gold or (gold and piece == gold[: len(piece)] and piece.startswith(gold[: min(20, len(gold))])):
            # Treat exact gold or truncated-gold prefix as the gold segment
            if piece == gold or (gold.startswith(piece) and len(piece) >= min(20, len(gold))):
                offset = cursor
                present = True
                break
        cursor += len(piece)
        if i + 1 < len(included):
            cursor += len(sep)
    if not present and gold and gold in packed:
        # Fallback: substring search (gold may only appear inside a filler)
        offset = packed.find(gold)
        present = offset >= 0

    n_fillers = sum(1 for p in included if p != gold)

    return PositionResult(
        position=position,
        packed_text=packed,
        estimate_tokens=estimate_tokens(packed),
        gold_present=present,
        gold_offset=offset,
        attention_risk=_RISK[position],
        n_fillers_used=n_fillers,
    )


def run_position_stress(
    gold: str,
    fillers: Sequence[str | dict[str, Any]],
    *,
    max_tokens: int = 512,
) -> PositionStressReport:
    """Build packed contexts with gold at first / middle / last.

    Args:
        gold: Gold evidence text that should appear in context.
        fillers: Distractor documents (strings or dicts with ``text``).
        max_tokens: Soft token budget using :func:`estimate_tokens` heuristic.

    Returns:
        :class:`PositionStressReport` with one :class:`PositionResult` per
        position and educational attention-risk labels.
    """
    if max_tokens < 1:
        raise ValueError("max_tokens must be >= 1")
    if not isinstance(gold, str) or not gold.strip():
        raise ValueError("gold must be a non-empty string")

    filler_texts = _as_texts(fillers)
    positions: list[PositionResult] = [
        _pack_at_position(gold, filler_texts, pos, max_tokens=max_tokens)
        for pos in ("first", "middle", "last")
    ]

    return PositionStressReport(
        gold=gold,
        max_tokens=max_tokens,
        positions=positions,
    )


def report_to_dict(report: PositionStressReport) -> dict[str, Any]:
    """Serialize a :class:`PositionStressReport` to a JSON-friendly dict."""
    return {
        "gold": report.gold,
        "max_tokens": report.max_tokens,
        "notes": report.notes,
        "positions": [
            {
                "position": p.position,
                "estimate_tokens": p.estimate_tokens,
                "gold_present": p.gold_present,
                "gold_offset": p.gold_offset,
                "attention_risk": p.attention_risk,
                "n_fillers_used": p.n_fillers_used,
                "packed_text": p.packed_text,
            }
            for p in report.positions
        ],
    }


def format_position_stress_report(report: PositionStressReport) -> str:
    """Human-readable lost-in-the-middle summary."""
    lines = [
        f"max_tokens: {report.max_tokens}",
        f"gold_chars: {len(report.gold)}",
        f"{'position':<8}  {'tokens':>6}  {'present':>7}  {'offset':>6}  {'risk':<6}  fillers",
        f"{'-' * 8}  {'-' * 6}  {'-' * 7}  {'-' * 6}  {'-' * 6}  -------",
    ]
    for p in report.positions:
        lines.append(
            f"{p.position:<8}  {p.estimate_tokens:6d}  {str(p.gold_present):>7}  "
            f"{p.gold_offset:6d}  {p.attention_risk:<6}  {p.n_fillers_used}"
        )
    lines.append(f"notes: {report.notes}")
    return "\n".join(lines) + "\n"


__all__ = [
    "AttentionRisk",
    "PositionName",
    "PositionResult",
    "PositionStressReport",
    "format_position_stress_report",
    "report_to_dict",
    "run_position_stress",
]
