"""Answer-quality rubric aligned with examples/evaluation-rubric.md spirit."""

from __future__ import annotations

from typing import Any

# Dimensions scoreable by humans or LLM-as-judge (0 / 1 / 2).
DIMENSIONS: tuple[str, ...] = (
    "groundedness",
    "relevance",
    "completeness",
    "citation_quality",
)

SCORE_MIN = 0
SCORE_MAX = 2
MAX_TOTAL = SCORE_MAX * len(DIMENSIONS)

# Fail closed on unsupported answers: groundedness must be at least 1.
GROUNDEDNESS_GATE = 1


def score_answer(scores: dict[str, int]) -> dict[str, Any]:
    """Aggregate per-dimension scores into a pass/fail scorecard.

    Args:
        scores: Mapping of dimension name → integer in ``{0, 1, 2}``.
            All of :data:`DIMENSIONS` must be present. Extra keys raise
            ``ValueError``.

    Returns:
        Dict with:

        - ``scores``: validated copy of input scores
        - ``total``: sum of dimension scores
        - ``max``: maximum possible total (:data:`MAX_TOTAL`)
        - ``passed``: ``True`` iff every score is in range **and**
          ``groundedness >= GROUNDEDNESS_GATE``
        - ``gate_failures``: list of human-readable gate failure reasons

    Raises:
        ValueError: Missing/unknown dimensions or out-of-range scores.
    """
    missing = [d for d in DIMENSIONS if d not in scores]
    if missing:
        raise ValueError(f"missing dimensions: {', '.join(missing)}")

    unknown = [k for k in scores if k not in DIMENSIONS]
    if unknown:
        raise ValueError(f"unknown dimensions: {', '.join(sorted(unknown))}")

    validated: dict[str, int] = {}
    for dim in DIMENSIONS:
        value = scores[dim]
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{dim} must be an int in {{{SCORE_MIN}..{SCORE_MAX}}}")
        if value < SCORE_MIN or value > SCORE_MAX:
            raise ValueError(
                f"{dim}={value} out of range [{SCORE_MIN}, {SCORE_MAX}]"
            )
        validated[dim] = value

    total = sum(validated.values())
    gate_failures: list[str] = []
    if validated["groundedness"] < GROUNDEDNESS_GATE:
        gate_failures.append(
            f"groundedness={validated['groundedness']} "
            f"< gate {GROUNDEDNESS_GATE}"
        )

    return {
        "scores": validated,
        "total": total,
        "max": MAX_TOTAL,
        "passed": len(gate_failures) == 0,
        "gate_failures": gate_failures,
    }


def format_scorecard(result: dict[str, Any]) -> str:
    """Render a :func:`score_answer` result as a plain-text scorecard."""
    lines: list[str] = ["RAG answer scorecard", "-" * 22]
    scores = result.get("scores", {})
    for dim in DIMENSIONS:
        if dim in scores:
            lines.append(f"  {dim}: {scores[dim]}/{SCORE_MAX}")
    total = result.get("total", 0)
    maximum = result.get("max", MAX_TOTAL)
    lines.append(f"  total: {total}/{maximum}")
    status = "PASS" if result.get("passed") else "FAIL"
    lines.append(f"  result: {status}")
    failures = result.get("gate_failures") or []
    if failures:
        lines.append("  gate failures:")
        for reason in failures:
            lines.append(f"    - {reason}")
    return "\n".join(lines) + "\n"
