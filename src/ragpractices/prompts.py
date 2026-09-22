"""Grounded answer / clarify prompt templates (stdlib only).

Templates only — no LLM or API calls. Useful for demos and for wiring into
an external chat completion client with fail-closed grounding instructions.
"""

from __future__ import annotations

from typing import Any, Sequence

_DEFAULT_MAX_CONTEXT_CHARS = 6000


def _context_text(item: str | dict[str, Any]) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("text") or item.get("document") or item.get("snippet") or "")
    raise TypeError("context items must be str or dict")


def _format_contexts(
    contexts: Sequence[str] | Sequence[dict[str, Any]],
    *,
    max_context_chars: int,
) -> tuple[str, int]:
    """Numbered [n] blocks, truncated to ``max_context_chars`` total."""
    if max_context_chars < 0:
        raise ValueError("max_context_chars must be >= 0")
    parts: list[str] = []
    used = 0
    count = 0
    for i, item in enumerate(contexts, start=1):
        text = _context_text(item).strip()
        if not text:
            continue
        header = f"[{i}] "
        remaining = max_context_chars - used
        if remaining <= len(header):
            break
        body = text if len(header) + len(text) <= remaining else text[: remaining - len(header)]
        block = header + body
        parts.append(block)
        used += len(block) + (2 if parts else 0)  # account for joining \n\n roughly
        count += 1
        if used >= max_context_chars:
            break
    joined = "\n\n".join(parts)
    if len(joined) > max_context_chars:
        joined = joined[:max_context_chars]
    return joined, count


def build_grounded_prompt(
    question: str,
    contexts: Sequence[str] | Sequence[dict[str, Any]],
    *,
    style: str = "cite",
    max_context_chars: int = _DEFAULT_MAX_CONTEXT_CHARS,
) -> str:
    """Build a system+user style prompt that insists on grounded answers.

    Templates only; does **not** call any API.

    Args:
        question: User question.
        contexts: Context strings or dicts with ``text`` / ``document`` /
            ``snippet``.
        style: ``"cite"`` (require ``[n]`` citations) or ``"abstain"``
            (emphasize refusing when context is insufficient).
        max_context_chars: Soft cap on total context characters.

    Returns:
        A single prompt string with system-style instructions, numbered
        context, and the question.
    """
    if style not in ("cite", "abstain"):
        raise ValueError("style must be 'cite' or 'abstain'")
    q = (question or "").strip()
    if not q:
        raise ValueError("question must be a non-empty string")

    ctx_block, n = _format_contexts(contexts, max_context_chars=max_context_chars)

    if style == "cite":
        instructions = (
            "You are a careful assistant. Answer using ONLY the provided "
            "context. Cite supporting passages as [n] matching the context "
            "numbers. If the context is insufficient, say you do not have "
            "enough information rather than guessing."
        )
    else:
        instructions = (
            "You are a careful assistant. Use ONLY the provided context. "
            "If the context does not contain enough information to answer "
            "confidently, ABSTAIN: reply that you cannot answer from the "
            "given sources. Do not invent facts. When you can answer, cite "
            "as [n]."
        )

    lines = [
        "### System",
        instructions,
        "",
        "### Context",
    ]
    if n == 0 or not ctx_block.strip():
        lines.append("(no context provided)")
    else:
        lines.append(ctx_block)
    lines.extend(
        [
            "",
            "### Question",
            q,
            "",
            "### Answer",
        ]
    )
    return "\n".join(lines) + "\n"


def build_clarify_prompt(
    question: str,
    missing_hints: Sequence[str] | None = None,
) -> str:
    """Build a short prompt that asks the user to clarify missing details.

    Templates only; does **not** call any API.

    Args:
        question: Original user question.
        missing_hints: Optional list of what is unclear (e.g. order id,
            date range).

    Returns:
        A prompt string instructing the model to ask clarifying questions.
    """
    q = (question or "").strip()
    if not q:
        raise ValueError("question must be a non-empty string")
    hints = [str(h).strip() for h in (missing_hints or []) if str(h).strip()]

    lines = [
        "### System",
        "The retrieved context appears incomplete or ambiguous. Ask the user "
        "brief clarifying questions before answering. Do not invent facts.",
        "",
        "### Question",
        q,
    ]
    if hints:
        lines.append("")
        lines.append("### Missing / unclear")
        for h in hints:
            lines.append(f"- {h}")
    lines.extend(["", "### Clarifying reply", ""])
    return "\n".join(lines)
