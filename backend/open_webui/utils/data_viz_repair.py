"""
Repair-model helper for the `show_widget` data-viz tool.

When the iframe rendering a widget throws a runtime error, the tool re-prompts
the model (with a focused fix-this prompt) to get back corrected widget HTML/JS
plus a tiny summary of what was fixed. This module isolates that model call so
the tool itself can stay focused on orchestration.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional, TypedDict

from fastapi import Request

from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.data_viz_prompts import assemble_data_viz_system_prompt
from open_webui.utils.task import get_task_model_id


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class RepairResult(TypedDict, total=False):
    widget_code: str
    summary: str


_FENCE_RE = re.compile(
    r"^\s*```(?:json|html|svg|xml)?\s*\n?(.*?)\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)


def _strip_fences(text: str) -> str:
    text = (text or "").strip()
    m = _FENCE_RE.match(text)
    return m.group(1).strip() if m else text


def _parse_repair_output(text: str) -> Optional[RepairResult]:
    """Try to parse the model output as JSON {widget_code, summary}.
    Falls back to treating the whole output as widget_code with a generic
    summary if JSON parsing fails."""
    cleaned = _strip_fences(text)
    if not cleaned:
        return None

    # Try JSON first.
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            wc = obj.get("widget_code")
            if isinstance(wc, str) and wc.lstrip().startswith("<"):
                summary = obj.get("summary")
                if not isinstance(summary, str):
                    summary = ""
                return {
                    "widget_code": wc.strip(),
                    "summary": summary.strip()[:120],
                }
    except json.JSONDecodeError:
        pass

    # Fallback: maybe the model ignored our format and just emitted HTML.
    if cleaned.lstrip().startswith("<"):
        return {
            "widget_code": cleaned,
            "summary": "",  # caller will substitute a generic summary
        }

    return None


def _pick_repair_model(cfg: Any, models: dict, original_model_id: Optional[str]) -> Optional[str]:
    """Admin override → original chat model → task-model fallback."""
    override = (getattr(cfg, "DATA_VIZ_AUTO_REPAIR_MODEL", "") or "").strip()
    for candidate in (override, original_model_id):
        if candidate and candidate in models:
            return candidate
    if not models:
        return None
    base = original_model_id if original_model_id and original_model_id in models else next(iter(models.keys()))
    try:
        return get_task_model_id(
            base,
            cfg.TASK_MODEL,
            cfg.TASK_MODEL_EXTERNAL,
            models,
        )
    except Exception:
        return base


def _build_messages(
    cfg: Any,
    title: str,
    widget_code: str,
    error_message: str,
    error_stack: Optional[str],
) -> list[dict]:
    system = assemble_data_viz_system_prompt(cfg) or ""
    stack_block = f"\nStack (top frames):\n{error_stack[:1200]}\n" if error_stack else ""
    user_msg = (
        "The `show_widget` tool you just called rendered into a sandboxed "
        "iframe and threw a runtime error.\n"
        f"\nError: {error_message[:500]}"
        f"{stack_block}"
        f"\nOriginal widget_code (title={title!r}):\n<<<\n{widget_code}\n>>>\n"
        "\nReturn ONLY a single JSON object with these two keys (no markdown "
        "fences, no commentary):\n"
        '  {"widget_code": "<corrected HTML fragment, NOT a full document — '
        'no <!DOCTYPE>, <html>, <head>, <body>>",\n'
        '   "summary": "<10 words or fewer describing what you fixed>"}\n'
        "\nUse the same iframe CSS variables as the original. Same intent and "
        "visual structure — fix the bug, do not rewrite the whole widget."
    )
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_msg})
    return messages


async def call_repair_model(
    *,
    request: Request,
    user: Any,
    cfg: Any,
    title: str,
    widget_code: str,
    error_message: str,
    error_stack: Optional[str],
    original_model_id: Optional[str],
    attempt: int,
) -> Optional[RepairResult]:
    """One repair attempt. Returns None on failure (model error, parse error,
    invalid output). The caller decides whether to retry."""
    models = request.app.state.MODELS
    model_id = _pick_repair_model(cfg, models, original_model_id)
    if not model_id:
        log.warning("data_viz repair: no usable model")
        return None

    messages = _build_messages(cfg, title, widget_code, error_message, error_stack)

    payload: dict = {
        "model": model_id,
        "messages": messages,
        "stream": False,
        "metadata": {
            **(request.state.metadata if hasattr(request.state, "metadata") else {}),
            "task": "data_viz_repair",
        },
    }

    # Optional reasoning_effort. Empty/missing = don't send the param at all
    # (so non-reasoning models don't error). Backend converts reasoning_effort
    # → {reasoning: {effort: ...}} canonical form before dispatch.
    effort = (getattr(cfg, "DATA_VIZ_AUTO_REPAIR_REASONING_EFFORT", "") or "").strip().lower()
    if effort in ("low", "medium", "high"):
        payload["reasoning_effort"] = effort

    log.info(
        "data_viz repair: attempt=%s model=%s error=%r",
        attempt, model_id, error_message[:120],
    )

    try:
        response = await generate_chat_completion(request, form_data=payload, user=user)
    except Exception:
        log.exception("data_viz repair: completion failed")
        return None

    text: Optional[str] = None
    try:
        if isinstance(response, dict):
            choices = response.get("choices") or []
            if choices:
                text = (choices[0].get("message") or {}).get("content")
    except Exception:
        text = None

    if not text:
        log.warning("data_viz repair: empty completion content")
        return None

    parsed = _parse_repair_output(text)
    if parsed is None:
        log.warning(
            "data_viz repair: model returned non-parseable output (len=%s, head=%r)",
            len(text), text[:120],
        )
        return None
    if not parsed.get("summary"):
        # Provide a generic placeholder so the caller can still report something.
        parsed["summary"] = "auto-repaired runtime error"
    return parsed
