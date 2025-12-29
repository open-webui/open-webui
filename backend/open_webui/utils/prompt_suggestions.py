import time
from typing import Any, Optional

DEFAULT_PROMPT_SUGGESTIONS_KEY = "default"


def build_prompt_suggestions_entry(
    suggestions: list, generated_at: Optional[int] = None, doc_hash: str = ""
) -> dict:
    if generated_at is None:
        generated_at = int(time.time())

    return {
        "suggestions": suggestions,
        "generated_at": int(generated_at),
        "doc_hash": doc_hash or "",
    }


def normalize_prompt_suggestions(value: Any, fallback_suggestions: list) -> dict:
    if isinstance(value, list):
        return {
            DEFAULT_PROMPT_SUGGESTIONS_KEY: build_prompt_suggestions_entry(
                value, generated_at=0
            )
        }

    if isinstance(value, dict):
        if "suggestions" in value:
            return {
                DEFAULT_PROMPT_SUGGESTIONS_KEY: build_prompt_suggestions_entry(
                    value.get("suggestions", fallback_suggestions),
                    generated_at=value.get("generated_at", 0),
                    doc_hash=value.get("doc_hash", ""),
                )
            }

        normalized = {}
        for key, entry in value.items():
            if not isinstance(key, str):
                continue
            if isinstance(entry, dict):
                suggestions = entry.get("suggestions", fallback_suggestions)
                generated_at = entry.get("generated_at", 0)
                doc_hash = entry.get("doc_hash", "")
            else:
                suggestions = fallback_suggestions
                generated_at = 0
                doc_hash = ""

            normalized[key] = build_prompt_suggestions_entry(
                suggestions,
                generated_at=generated_at,
                doc_hash=doc_hash,
            )

        if DEFAULT_PROMPT_SUGGESTIONS_KEY not in normalized:
            normalized[DEFAULT_PROMPT_SUGGESTIONS_KEY] = build_prompt_suggestions_entry(
                fallback_suggestions, generated_at=0
            )

        return normalized

    return {
        DEFAULT_PROMPT_SUGGESTIONS_KEY: build_prompt_suggestions_entry(
            fallback_suggestions, generated_at=0
        )
    }


def is_prompt_suggestions_stale(entry: dict, ttl_seconds: int) -> bool:
    if ttl_seconds <= 0:
        return False
    generated_at = entry.get("generated_at", 0)
    if not isinstance(generated_at, (int, float)):
        return True
    return (time.time() - float(generated_at)) > ttl_seconds
