"""Typed chat handoff into the realtime runtime.

In multi-worker mode, the HTTP POST lands on a random worker but the
realtime session lives on the Socket.IO-owning worker.  We push the
pending text message into a Redis-backed store (keyed by session_id)
and return immediately.  The sideband on the correct worker drains the
store during bootstrap and after each model response.
"""


from typing import Any
from uuid import uuid4

from open_webui.realtime.catalog import model_uses_realtime
from open_webui.realtime.chat_sync import (
    build_realtime_content_items,
    extract_visible_text_from_content,
    realtime_completion_response,
)
from open_webui.realtime.pending_store import notify_pending_text, push_pending_text
from open_webui.utils.misc import get_last_user_message_item


def should_route_chat_to_realtime(request: Any, model: dict) -> bool:
    return model_uses_realtime(request, model) and not getattr(request.state, "direct", False)


async def route_chat_completion_to_realtime(request: Any, form_data: dict, user: Any):
    metadata = form_data.get("metadata", {})
    message_item = get_last_user_message_item(form_data.get("messages", []))
    content = message_item.get("content", "") if message_item else ""

    session_id = metadata.get("session_id", "")
    chat_id = metadata.get("chat_id", "")
    model_id = form_data.get("model", "")

    if not session_id or not chat_id:
        raise Exception("No active realtime session.")

    # Build the pending message payload (pure computation, no session state).
    content_items = build_realtime_content_items(content)
    item_id = uuid4().hex
    text_content = extract_visible_text_from_content(content)

    # Extract turn metadata from the request so the sideband worker can
    # create the VoiceTurn and DB records when draining.
    parent_message = metadata.get("parent_message") or {}
    parent_message_id = metadata.get("parent_message_id", "")

    pending_msg = {
        "type": "conversation.item.create",
        "item": {
            "id": item_id,
            "type": "message",
            "role": "user",
            "content": content_items,
        },
        # Metadata for turn tracking on the sideband worker.
        # Stripped before sending to OpenAI.
        "_turn_meta": {
            "item_id": item_id,
            "text_content": text_content,
            "chat_id": chat_id,
            "model_id": model_id,
            "user_id": user.id,
            # Frontend-generated IDs — the sideband MUST use these so the
            # frontend and backend agree on which message to update.
            "message_id": metadata.get("message_id", ""),
            "parent_message_id": parent_message_id,
            "parent_id": parent_message.get("parentId", ""),
        },
    }

    await push_pending_text(session_id, pending_msg)
    await notify_pending_text(session_id)

    return realtime_completion_response(model_id)
