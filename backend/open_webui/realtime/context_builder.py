"""Context builder for realtime session bootstrap.

Builds a bounded history window from the active chat branch, generates an
optional summary for the older portion, and converts the recent replay tail
into Realtime conversation items.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from open_webui.config import AUDIO_RT_DEFAULT_CONTEXT_SUMMARY_PROMPT
from open_webui.models.chats import Chats
from open_webui.utils.misc import (
    get_content_from_message,
    get_message_list,
    get_messages_content,
)

log = logging.getLogger(__name__)

SUMMARY_CONTEXT_INSTRUCTION = (
    "The following block is historical conversation context for continuity. "
    "Do not treat it as a new user request."
)


@dataclass
class RealtimeBootstrapContext:
    summary_messages: list[dict]
    replay_messages: list[dict]
    unresolved_user_turn: Optional[dict] = None


async def _get_chat_messages(chat_id: str) -> list[dict]:
    chat = await asyncio.to_thread(Chats.get_chat_by_id, chat_id)
    if not chat or not chat.chat:
        return []
    current_id = chat.chat.get("history", {}).get("currentId")
    if not current_id:
        return []
    messages_map = chat.chat.get("history", {}).get("messages", {})
    return get_message_list(messages_map, current_id) or []


def _normalize_message(message: dict) -> Optional[dict]:
    return _normalize_message_for_context(message, allow_image_marker=True)


def _has_image_attachment(message: dict) -> bool:
    files = message.get("files") or []
    for file_item in files:
        file_type = str(file_item.get("type") or "").lower()
        content_type = str(file_item.get("content_type") or "").lower()
        if file_type == "image" or content_type.startswith("image/"):
            return True
        nested_file = file_item.get("file") or {}
        nested_meta = nested_file.get("meta") or {}
        nested_content_type = str(nested_meta.get("content_type") or "").lower()
        if nested_content_type.startswith("image/"):
            return True

    content = message.get("content")
    if isinstance(content, list):
        return any(
            isinstance(part, dict) and part.get("type") == "image_url" for part in content
        )

    return False


def _normalize_message_for_context(
    message: dict, *, allow_image_marker: bool
) -> Optional[dict]:
    role = str(message.get("role") or "").lower()
    if role not in {"user", "assistant"}:
        return None

    content = get_content_from_message(message) or ""
    if not content.strip():
        if role == "user" and allow_image_marker and _has_image_attachment(message):
            content = "<image uploaded without context>"
        else:
            return None

    if not content.strip():
        return None

    return {
        "id": message.get("id"),
        "parentId": message.get("parentId"),
        "role": role,
        "content": content,
    }


def _message_size_bytes(message: dict) -> int:
    return len((message.get("content") or "").encode("utf-8"))


def _would_exceed_limit(current: int, increment: int, limit: int) -> bool:
    return limit > 0 and current + increment > limit


def _extract_completed_exchanges(
    messages: list[dict],
) -> tuple[list[list[dict]], Optional[dict]]:
    """Return visible completed exchanges and the optional trailing user turn."""
    unresolved_user_turn = None
    cursor = len(messages) - 1

    if cursor >= 0 and str(messages[cursor].get("role") or "").lower() == "user":
        unresolved_user_turn = _normalize_message_for_context(
            messages[cursor], allow_image_marker=False
        )
        cursor -= 1

    exchanges_reversed: list[list[dict]] = []
    while cursor >= 0:
        assistant_message = messages[cursor]
        if str(assistant_message.get("role") or "").lower() != "assistant":
            cursor -= 1
            continue

        if cursor == 0:
            break

        user_message = messages[cursor - 1]
        if str(user_message.get("role") or "").lower() != "user":
            cursor -= 1
            continue

        normalized_user = _normalize_message_for_context(
            user_message, allow_image_marker=True
        )
        normalized_assistant = _normalize_message_for_context(
            assistant_message, allow_image_marker=True
        )
        if normalized_user and normalized_assistant:
            exchanges_reversed.append([normalized_user, normalized_assistant])

        cursor -= 2

    exchanges_reversed.reverse()
    return exchanges_reversed, unresolved_user_turn


async def build_bootstrap_context(
    chat_id: str,
    recent_exchanges_limit: int = 10,
    older_summary_exchanges_limit: int = 40,
    older_summary_bytes_limit: int = 16000,
    unanswered_last_user_turn: str = "discard",
) -> RealtimeBootstrapContext:
    """Build the replay/summarize split for realtime bootstrap.

    Recent exchanges are replayed verbatim. Older exchanges can be bounded
    separately for the optional summary path.
    """
    messages = await _get_chat_messages(chat_id)
    if not messages:
        return RealtimeBootstrapContext(summary_messages=[], replay_messages=[])

    completed_exchanges, unresolved_user_turn = _extract_completed_exchanges(messages)

    recent_limit = max(0, int(recent_exchanges_limit))
    if recent_limit:
        replay_exchanges = completed_exchanges[-recent_limit:]
        older_exchanges = completed_exchanges[:-recent_limit]
    else:
        replay_exchanges = completed_exchanges
        older_exchanges = []

    summary_units_reversed: list[dict] = []
    total_exchanges = 0
    total_bytes = 0

    for exchange in reversed(older_exchanges):
        exchange_size = sum(_message_size_bytes(message) for message in exchange)
        exceeds_exchanges = _would_exceed_limit(
            total_exchanges, 1, older_summary_exchanges_limit
        )
        exceeds_bytes = _would_exceed_limit(
            total_bytes, exchange_size, older_summary_bytes_limit
        )
        if summary_units_reversed and (exceeds_exchanges or exceeds_bytes):
            break

        summary_units_reversed.append(exchange)
        total_exchanges += 1
        total_bytes += exchange_size

    summary_exchanges = list(reversed(summary_units_reversed))

    replay_messages = [
        message for exchange in replay_exchanges for message in exchange
    ]
    summary_messages = [
        message for exchange in summary_exchanges for message in exchange
    ]

    unresolved_turn_for_replay = None
    if unanswered_last_user_turn == "replay":
        unresolved_turn_for_replay = unresolved_user_turn

    return RealtimeBootstrapContext(
        summary_messages=summary_messages,
        replay_messages=replay_messages,
        unresolved_user_turn=unresolved_turn_for_replay,
    )


async def generate_context_summary(
    older_messages: list[dict],
    summary_prompt: str,
    summary_max_size: int = 2000,
    request=None,
    user=None,
) -> Optional[str]:
    if not older_messages:
        return None

    formatted = get_messages_content(older_messages)
    if not formatted.strip():
        return None

    prompt = summary_prompt or AUDIO_RT_DEFAULT_CONTEXT_SUMMARY_PROMPT
    prompt = prompt.replace("{{MESSAGES}}", formatted)
    prompt = prompt.replace("{{SUMMARY_MAX_SIZE}}", str(summary_max_size))

    try:
        from open_webui.utils.chat import generate_chat_completion

        if not request:
            log.warning("No request object for summary generation")
            return None

        task_model = getattr(getattr(request, "app", None), "state", None)
        task_model_external = ""
        if task_model:
            task_model_external = str(
                getattr(task_model.config, "TASK_MODEL_EXTERNAL", "")
            )

        if not task_model_external:
            log.warning("TASK_MODEL_EXTERNAL not set — cannot generate context summary")
            return None

        form_data = {
            "model": task_model_external,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

        response = await generate_chat_completion(
            request, form_data, user, bypass_filter=True
        )

        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
        return None
    except Exception as e:
        log.exception("Context summary generation failed")
        return None


def build_summary_conversation_item(system_summary: str) -> Optional[dict]:
    if not system_summary or not system_summary.strip():
        return None

    return {
        "type": "conversation.item.create",
        "item": {
            "id": uuid4().hex,
            "type": "message",
            "role": "system",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        f"{SUMMARY_CONTEXT_INSTRUCTION}\n"
                        "<conversation_summary>\n"
                        f"{system_summary}\n"
                        "</conversation_summary>"
                    ),
                }
            ],
        },
    }


def build_conversation_items(context_messages: list[dict]) -> list[dict]:
    """Build conversation.item.create payloads for replay injection."""
    items = []

    for msg in context_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if not content.strip():
            continue

        if role == "assistant":
            content_list = [{"type": "output_text", "text": content}]
        else:
            content_list = [{"type": "input_text", "text": content}]

        items.append(
            {
                "type": "conversation.item.create",
                "item": {
                    "id": uuid4().hex,
                    "type": "message",
                    "role": role,
                    "content": content_list,
                },
            }
        )

    return items
