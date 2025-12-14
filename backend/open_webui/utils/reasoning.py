from __future__ import annotations

from typing import Any


def extract_reasoning_content(
    delta: dict[str, Any],
    reasoning_details: list[dict[str, Any]] | None = None,
) -> str | None:
    """
    Extract a reasoning delta string from an OpenAI-compatible streaming delta.

    Some providers include the same reasoning text in both `reasoning_*` fields and
    `reasoning_details`. When both are present, prefer `reasoning_details` to avoid
    duplicated output.
    """

    reasoning_content = (
        delta.get("reasoning_content") or delta.get("reasoning") or delta.get("thinking")
    )

    if reasoning_details is None:
        reasoning_details = delta.get("reasoning_details")

    if isinstance(reasoning_details, list):
        reasoning_text_chunks = [
            detail.get("text", "")
            for detail in reasoning_details
            if detail.get("type") == "reasoning.text" and detail.get("text")
        ]

        if reasoning_text_chunks:
            return "".join(reasoning_text_chunks)

    return reasoning_content

