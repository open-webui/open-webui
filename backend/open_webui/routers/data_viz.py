"""
Auto-repair endpoint for the `show_widget` data-viz tool.

When the iframe rendering a widget throws a JavaScript error, the frontend
posts the error here. We re-prompt the model with the error + the broken
widget code, get back a corrected fragment, and (if possible) persist the
fix into the assistant message so reloads keep the working version.
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import re
import time
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.constants import TASKS
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.chats import Chats
from open_webui.routers.pipelines import process_pipeline_inlet_filter
from open_webui.utils.auth import get_verified_user
from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.data_viz_prompts import assemble_data_viz_system_prompt
from open_webui.utils.task import get_task_model_id

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class RepairRequest(BaseModel):
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
    title: str
    widget_code: str
    error_message: str
    error_stack: Optional[str] = None
    attempt: int = 1


class RepairResponse(BaseModel):
    success: bool
    widget_code: Optional[str] = None
    reason: Optional[str] = None  # 'feature_disabled' | 'max_attempts' | 'model_failed' | 'invalid_output' | 'no_chat'


# ---------------------------------------------------------------------------
# Tiny in-process LRU cache. Keyed on hash(widget_code + error_message). Avoids
# re-spending the model when the same broken widget renders twice (back/forward
# nav, reload, etc). Per-process — no Redis. Bounded.
# ---------------------------------------------------------------------------

_CACHE_TTL_S = 600  # 10 minutes
_CACHE_MAX = 200
_repair_cache: dict[str, tuple[float, str]] = {}


def _cache_key(widget_code: str, error_message: str) -> str:
    h = hashlib.sha256()
    h.update(widget_code.encode("utf-8", errors="replace"))
    h.update(b"\x00")
    h.update(error_message.encode("utf-8", errors="replace"))
    return h.hexdigest()


def _cache_get(key: str) -> Optional[str]:
    entry = _repair_cache.get(key)
    if not entry:
        return None
    ts, value = entry
    if time.time() - ts > _CACHE_TTL_S:
        _repair_cache.pop(key, None)
        return None
    return value


def _cache_put(key: str, value: str) -> None:
    if len(_repair_cache) >= _CACHE_MAX:
        # Drop oldest by timestamp
        oldest = min(_repair_cache.items(), key=lambda kv: kv[1][0])
        _repair_cache.pop(oldest[0], None)
    _repair_cache[key] = (time.time(), value)


# ---------------------------------------------------------------------------
# Persistence: rewrite the broken widget_code inside the assistant message.
# The wire format is double-encoded JSON inside an HTML attribute (mirrors
# MarkdownTokens.svelte:parseToolCallArguments).
# ---------------------------------------------------------------------------

_DETAILS_RE = re.compile(
    r'(<details\b[^>]*?\bname="show_widget"[^>]*?\barguments=")([^"]*)("[^>]*?>)',
    re.IGNORECASE | re.DOTALL,
)


def _decode_args_attribute(escaped: str) -> Tuple[Optional[dict], bool]:
    """Decode the html-escaped arguments attribute. Returns (dict, was_double_encoded)."""
    raw = html.unescape(escaped)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None, False

    double = False
    if isinstance(value, str):
        try:
            value = json.loads(value)
            double = True
        except json.JSONDecodeError:
            return None, False

    if not isinstance(value, dict):
        return None, double
    return value, double


def _encode_args_attribute(args: dict, double: bool) -> str:
    """Mirror the original encoding (single or double JSON) and html-escape."""
    inner = json.dumps(args, ensure_ascii=False)
    if double:
        inner = json.dumps(inner, ensure_ascii=False)
    return html.escape(inner)


def _replace_widget_in_content(
    content: str, original_widget_code: str, new_widget_code: str
) -> Tuple[str, bool]:
    """Find the first <details name="show_widget"> block whose decoded args
    have widget_code == original_widget_code, and substitute new_widget_code.
    Returns (new_content, replaced)."""
    for m in _DETAILS_RE.finditer(content):
        prefix, escaped, suffix = m.group(1), m.group(2), m.group(3)
        args, double = _decode_args_attribute(escaped)
        if args is None:
            continue
        if args.get("widget_code") != original_widget_code:
            continue
        args["widget_code"] = new_widget_code
        new_attr = _encode_args_attribute(args, double)
        return (
            content[: m.start()] + prefix + new_attr + suffix + content[m.end():],
            True,
        )
    return content, False


def _persist_repair(
    chat_id: str,
    message_id: str,
    original_widget_code: str,
    new_widget_code: str,
    user_id: str,
) -> bool:
    """Best-effort: rewrite the broken widget in the chat history. Returns
    True if the message was updated. Logs and returns False on any failure
    (the in-page fix still works without persistence)."""
    try:
        chat = Chats.get_chat_by_id(chat_id)
        if chat is None or chat.user_id != user_id:
            return False
        chat_dict = chat.chat or {}
        history = chat_dict.get("history", {}) or {}
        messages = history.get("messages", {}) or {}
        msg = messages.get(message_id)
        if not msg or "content" not in msg:
            return False
        new_content, replaced = _replace_widget_in_content(
            msg["content"], original_widget_code, new_widget_code
        )
        if not replaced:
            return False
        msg["content"] = new_content
        messages[message_id] = msg
        history["messages"] = messages
        chat_dict["history"] = history
        Chats.update_chat_by_id(chat_id, chat_dict)
        return True
    except Exception:
        log.exception("data_viz repair: persistence failed for chat=%s msg=%s", chat_id, message_id)
        return False


# ---------------------------------------------------------------------------
# Repair prompt + completion
# ---------------------------------------------------------------------------


def _build_repair_messages(
    config,
    user_request_excerpt: str,
    title: str,
    widget_code: str,
    error_message: str,
    error_stack: Optional[str],
) -> list[dict]:
    """System prompt = full data_viz scaffolding so the model knows the rules.
    User prompt = focused fix-this with error + original code."""
    system = assemble_data_viz_system_prompt(config) or ""

    stack_block = f"\nStack (top frames):\n{error_stack}\n" if error_stack else ""
    intent_block = (
        f"\nThe user originally asked for:\n<<<\n{user_request_excerpt}\n>>>\n"
        if user_request_excerpt
        else ""
    )

    user_msg = (
        f"The `show_widget` tool you just called rendered into a sandboxed iframe and "
        f"threw a runtime error.\n"
        f"\nError: {error_message}"
        f"{stack_block}"
        f"{intent_block}"
        f"\nOriginal widget_code (title={title!r}):\n<<<\n{widget_code}\n>>>\n"
        f"\nReturn ONLY the corrected widget_code as a raw HTML fragment — NOT a "
        f"full document, no <!DOCTYPE>, <html>, <head>, or <body>. No markdown "
        f"fences. No commentary. Use the same iframe CSS variables as the "
        f"original. Same intent and visual structure — fix the bug, don't "
        f"rewrite the whole widget."
    )

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_msg})
    return messages


_FENCE_RE = re.compile(r"^\s*```(?:html|svg|xml)?\s*\n?(.*?)\n?```\s*$", re.DOTALL | re.IGNORECASE)


def _strip_fences(text: str) -> str:
    """Strip ```html ... ``` or bare ``` ... ``` if the model wrapped output."""
    m = _FENCE_RE.match(text.strip())
    if m:
        return m.group(1).strip()
    return text.strip()


def _looks_like_html_fragment(text: str) -> bool:
    """Cheap validation — must start with '<' and contain a tag close."""
    s = text.lstrip()
    return s.startswith("<") and ">" in s


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/repair", response_model=RepairResponse)
async def repair_widget(
    request: Request,
    form_data: RepairRequest,
    user=Depends(get_verified_user),
):
    cfg = request.app.state.config

    if not getattr(cfg, "ENABLE_DATA_VIZ", False):
        return RepairResponse(success=False, reason="feature_disabled")
    if not getattr(cfg, "DATA_VIZ_AUTO_REPAIR_ENABLED", True):
        return RepairResponse(success=False, reason="feature_disabled")

    max_attempts = max(1, min(int(getattr(cfg, "DATA_VIZ_AUTO_REPAIR_MAX_ATTEMPTS", 3)), 5))
    if form_data.attempt > max_attempts:
        return RepairResponse(success=False, reason="max_attempts")

    if not form_data.widget_code or not form_data.error_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="widget_code and error_message are required",
        )

    # Cache hit? Identical broken widget + identical error → reuse.
    ckey = _cache_key(form_data.widget_code, form_data.error_message)
    cached = _cache_get(ckey)
    if cached:
        log.info("data_viz repair: cache hit (chat=%s msg=%s attempt=%s)",
                 form_data.chat_id, form_data.message_id, form_data.attempt)
        if form_data.chat_id and form_data.message_id:
            _persist_repair(form_data.chat_id, form_data.message_id,
                            form_data.widget_code, cached, user.id)
        return RepairResponse(success=True, widget_code=cached)

    # Pull original user-request context from the chat (best effort).
    user_request_excerpt = ""
    chat_model_id: Optional[str] = None
    if form_data.chat_id:
        try:
            chat = Chats.get_chat_by_id(form_data.chat_id)
            if chat and chat.user_id == user.id:
                history = (chat.chat or {}).get("history", {}) or {}
                messages = history.get("messages", {}) or {}
                msg = messages.get(form_data.message_id) if form_data.message_id else None
                # Walk back to nearest user message
                while msg and msg.get("role") != "user":
                    parent_id = msg.get("parentId")
                    if not parent_id:
                        break
                    msg = messages.get(parent_id)
                if msg and msg.get("role") == "user":
                    user_request_excerpt = (msg.get("content") or "")[:800]
                # Also pick the assistant message's model so repair runs on the
                # same backend the original used (matters for tool-calling models).
                target_msg = messages.get(form_data.message_id) if form_data.message_id else None
                if target_msg:
                    chat_model_id = (
                        target_msg.get("selectedModelId")
                        or target_msg.get("model")
                    )
        except Exception:
            log.exception("data_viz repair: failed to read chat context")

    # Pick the model: admin override → original chat model → task model.
    repair_model_override = (getattr(cfg, "DATA_VIZ_AUTO_REPAIR_MODEL", "") or "").strip()
    models = request.app.state.MODELS
    model_id: Optional[str] = None
    for candidate in (repair_model_override, chat_model_id):
        if candidate and candidate in models:
            model_id = candidate
            break
    if model_id is None:
        # Fall back: any user-accessible model the task pipeline would pick.
        if chat_model_id and chat_model_id in models:
            model_id = chat_model_id
        else:
            # Pick the first available model as a last resort.
            try:
                model_id = next(iter(models.keys()))
            except StopIteration:
                return RepairResponse(success=False, reason="model_failed")
        # Also defer to task-model selection so admin policy still applies.
        try:
            model_id = get_task_model_id(
                model_id,
                cfg.TASK_MODEL,
                cfg.TASK_MODEL_EXTERNAL,
                models,
            )
        except Exception:
            pass

    messages = _build_repair_messages(
        cfg,
        user_request_excerpt,
        form_data.title,
        form_data.widget_code,
        form_data.error_message,
        form_data.error_stack,
    )

    payload = {
        "model": model_id,
        "messages": messages,
        "stream": False,
        "metadata": {
            **(request.state.metadata if hasattr(request.state, "metadata") else {}),
            "task": "data_viz_repair",
            "chat_id": form_data.chat_id,
        },
    }

    log.info(
        "data_viz repair: chat=%s msg=%s attempt=%s model=%s err=%r",
        form_data.chat_id, form_data.message_id, form_data.attempt, model_id,
        form_data.error_message[:120],
    )

    try:
        payload = await process_pipeline_inlet_filter(request, payload, user, models)
    except Exception:
        log.exception("data_viz repair: pipeline filter failed")

    try:
        response = await generate_chat_completion(request, form_data=payload, user=user)
    except Exception:
        log.exception("data_viz repair: completion failed")
        return RepairResponse(success=False, reason="model_failed")

    # Pull text out of the OpenAI-style response.
    text: Optional[str] = None
    try:
        choices = response.get("choices") if isinstance(response, dict) else None
        if choices:
            text = choices[0].get("message", {}).get("content")
    except Exception:
        text = None

    if not text:
        return RepairResponse(success=False, reason="model_failed")

    cleaned = _strip_fences(text)
    if not _looks_like_html_fragment(cleaned):
        log.warning("data_viz repair: model returned non-HTML output (len=%s)", len(cleaned))
        return RepairResponse(success=False, reason="invalid_output")

    _cache_put(ckey, cleaned)

    if form_data.chat_id and form_data.message_id:
        persisted = _persist_repair(
            form_data.chat_id, form_data.message_id,
            form_data.widget_code, cleaned, user.id,
        )
        if not persisted:
            log.info("data_viz repair: persistence skipped/failed; in-page fix still applies")

    return RepairResponse(success=True, widget_code=cleaned)
