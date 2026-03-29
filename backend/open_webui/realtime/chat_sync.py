"""Realtime chat/turn persistence helpers."""


import asyncio
import logging
import time
from typing import Any, Optional
from uuid import uuid4

from open_webui.constants import TASKS
from open_webui.models.chats import ChatForm, Chats
from open_webui.realtime.constants import (
    ASSISTANT_LISTENING_PLACEHOLDER,
    USER_TRANSCRIBING_PLACEHOLDER,
)
from open_webui.realtime.session_state import RealtimeSession
from open_webui.realtime.turn_state import VoiceTurn

log = logging.getLogger(__name__)


def _is_realtime_voice_placeholder(content: Any) -> bool:
    return content in ("", USER_TRANSCRIBING_PLACEHOLDER, ASSISTANT_LISTENING_PLACEHOLDER)


async def _get_chat_history_messages(chat_id: str) -> tuple[Optional[Any], dict]:
    chat = await asyncio.to_thread(Chats.get_chat_by_id, chat_id)
    if not chat or not chat.chat:
        return None, {}

    return chat, chat.chat.get("history", {}).get("messages", {})


async def run_session_end_background_tasks(session: RealtimeSession) -> None:
    try:
        if not session.event_emitter_factory:
            return

        chat = await asyncio.to_thread(Chats.get_chat_by_id, session.chat_id)
        if not chat or not chat.chat:
            return

        history = chat.chat.get("history", {})
        current_id = history.get("currentId", "")
        if not current_id:
            return

        last_message = history.get("messages", {}).get(current_id)
        if not last_message:
            return

        event_emitter = session.event_emitter_factory(
            {
                "user_id": session.user_id,
                "chat_id": session.chat_id,
                "message_id": current_id,
            }
        )

        tasks = {
            TASKS.TITLE_GENERATION: True,
            TASKS.TAGS_GENERATION: True,
            TASKS.FOLLOW_UP_GENERATION: True,
        }

        ctx = {
            "request": session.tool_request,
            "form_data": {
                "model": session.model_id,
                "messages": [],
            },
            "user": session.user,
            "metadata": {
                "chat_id": session.chat_id,
                "message_id": current_id,
            },
            "tasks": tasks,
            "events": [],
            "event_emitter": event_emitter,
        }

        from open_webui.utils.middleware import background_tasks_handler

        await background_tasks_handler(ctx)
    except Exception as exc:
        log.exception("Error running session-end background tasks")


async def ensure_chat_created(session: RealtimeSession, sio) -> bool:
    """Create a real chat if the session still has a local: chat_id."""
    async with session._chat_creation_lock:
        if not session.chat_id.startswith("local:"):
            return True

        new_chat = await asyncio.to_thread(
            Chats.insert_new_chat,
            user_id=session.user_id,
            form_data=ChatForm(
                chat={
                    "title": "New Chat",
                    "history": {"messages": {}, "currentId": ""},
                }
            ),
        )
        if not new_chat:
            log.error("Failed to create chat for realtime session")
            return False

        old_chat_id = session.chat_id
        session.chat_id = new_chat.id
        await sio.emit(
            "rt:chat_id_update",
            {"old_id": old_chat_id, "new_id": new_chat.id},
            room=session.session_id,
        )
        return True


async def ensure_realtime_voice_turn(
    session: RealtimeSession, sio, item_id: str = ""
) -> Optional[VoiceTurn]:
    if item_id:
        existing_turn = session.turn_state.get_turn_by_input_item(item_id)
        if existing_turn:
            return existing_turn

    if not await ensure_chat_created(session, sio):
        return None

    turn_id = str(uuid4())
    user_message_id = str(uuid4())
    assistant_message_id = str(uuid4())

    chat = await asyncio.to_thread(Chats.get_chat_by_id, session.chat_id)
    parent_id = ""
    if chat and chat.chat:
        parent_id = chat.chat.get("history", {}).get("currentId", "")

    turn = session.turn_state.create_turn(
        turn_id=turn_id,
        user_message_id=user_message_id,
        assistant_message_id=assistant_message_id,
        parent_message_id=parent_id,
    )
    if item_id:
        session.turn_state.bind_input_item(item_id, turn_id)

    await create_voice_turn_messages(
        chat_id=session.chat_id,
        parent_id=parent_id,
        user_msg_id=user_message_id,
        asst_msg_id=assistant_message_id,
        model_id=session.model_id,
        user_content=USER_TRANSCRIBING_PLACEHOLDER,
        assistant_content=ASSISTANT_LISTENING_PLACEHOLDER,
    )

    await emit_to_user(
        sio,
        session.user_id,
        session.chat_id,
        assistant_message_id,
        {
            "type": "chat:message:create",
            "data": {
                "chatId": session.chat_id,
                "parentId": parent_id,
                "userMessage": {
                    "id": user_message_id,
                    "role": "user",
                    "content": USER_TRANSCRIBING_PLACEHOLDER,
                },
                "assistantMessage": {
                    "id": assistant_message_id,
                    "role": "assistant",
                    "content": ASSISTANT_LISTENING_PLACEHOLDER,
                    "model": session.model_id,
                },
                "currentId": assistant_message_id,
            },
        },
    )
    return turn


async def create_voice_turn_messages(
    chat_id: str,
    parent_id: str,
    user_msg_id: str,
    asst_msg_id: str,
    model_id: str,
    user_content: str = "",
    assistant_content: str = "",
) -> None:
    """Create linked user + assistant message nodes in the chat DB."""
    now = int(time.time())

    user_msg = {
        "id": user_msg_id,
        "parentId": parent_id,
        "childrenIds": [asst_msg_id],
        "role": "user",
        "content": user_content,
        "timestamp": now,
    }

    asst_msg = {
        "id": asst_msg_id,
        "parentId": user_msg_id,
        "childrenIds": [],
        "role": "assistant",
        "content": assistant_content,
        "model": model_id,
        "timestamp": now,
    }

    await asyncio.to_thread(
        Chats.upsert_message_to_chat_by_id_and_message_id, chat_id, user_msg_id, user_msg
    )
    await asyncio.to_thread(
        Chats.upsert_message_to_chat_by_id_and_message_id, chat_id, asst_msg_id, asst_msg
    )

    if parent_id:
        chat = await asyncio.to_thread(Chats.get_chat_by_id, chat_id)
        if chat and chat.chat:
            messages_map = chat.chat.get("history", {}).get("messages", {})
            parent_msg = messages_map.get(parent_id)
            if parent_msg:
                children = parent_msg.get("childrenIds", [])
                if user_msg_id not in children:
                    children.append(user_msg_id)
                    await asyncio.to_thread(
                        Chats.upsert_message_to_chat_by_id_and_message_id,
                        chat_id,
                        parent_id,
                        {"childrenIds": children},
                        advance_current=False,
                    )


async def _create_assistant_reply_message(
    chat_id: str,
    user_msg_id: str,
    model_id: str,
    assistant_content: str = "",
) -> Optional[str]:
    """Create a new assistant child for an existing stored user message."""
    chat = await asyncio.to_thread(Chats.get_chat_by_id, chat_id)
    if not chat or not chat.chat:
        return None

    messages_map = chat.chat.get("history", {}).get("messages", {})
    user_message = messages_map.get(user_msg_id)
    if not user_message:
        return None

    assistant_message_id = str(uuid4())
    now = int(time.time())
    children = list(user_message.get("childrenIds", []) or [])
    if assistant_message_id not in children:
        children.append(assistant_message_id)

    await asyncio.to_thread(
        Chats.upsert_message_to_chat_by_id_and_message_id,
        chat_id, user_msg_id, {"childrenIds": children}, advance_current=False,
    )
    await asyncio.to_thread(
        Chats.upsert_message_to_chat_by_id_and_message_id,
        chat_id, assistant_message_id,
        {
            "id": assistant_message_id,
            "parentId": user_msg_id,
            "childrenIds": [],
            "role": "assistant",
            "content": assistant_content,
            "model": model_id,
            "timestamp": now,
        },
    )

    return assistant_message_id


async def resolve_realtime_voice_assistant_reply_message(
    chat_id: str,
    user_msg_id: str,
    model_id: str,
    assistant_content: str = "",
) -> Optional[str]:
    chat, messages_map = await _get_chat_history_messages(chat_id)
    if not chat:
        return None

    user_message = messages_map.get(user_msg_id)
    if not user_message:
        return None

    assistant_children = []
    realtime_voice_children = []
    for child_id in user_message.get("childrenIds", []) or []:
        child_message = messages_map.get(child_id)
        if not child_message or child_message.get("role") != "assistant":
            continue

        assistant_children.append(child_message)
        if child_message.get("content", "") == ASSISTANT_LISTENING_PLACEHOLDER:
            realtime_voice_children.append(child_message)

    if len(realtime_voice_children) == 1:
        assistant_message = realtime_voice_children[0]
        assistant_message_id = assistant_message.get("id")
        if assistant_message_id and assistant_content:
            await asyncio.to_thread(
                Chats.upsert_message_to_chat_by_id_and_message_id,
                chat_id, assistant_message_id,
                {
                    "id": assistant_message_id,
                    "role": "assistant",
                    "content": assistant_content,
                    "model": model_id,
                    "timestamp": assistant_message.get("timestamp", int(time.time())),
                },
                advance_current=False,
            )
        return assistant_message_id

    if len(realtime_voice_children) > 1 or assistant_children:
        log.warning(
            "Ambiguous realtime voice assistant children for chat=%s user=%s; "
            "refusing to create another branch",
            chat_id,
            user_msg_id,
        )
        return None

    return await _create_assistant_reply_message(
        chat_id,
        user_msg_id,
        model_id,
        assistant_content=assistant_content,
    )


async def remove_orphan_turn_messages(
    chat_id: str, user_msg_id: str, asst_msg_id: str, parent_id: str
) -> None:
    """Remove orphan user+assistant messages from an empty/pruned turn."""
    from open_webui.realtime.chat_merge import build_realtime_delete_patch, merge_chat_payload

    chat = await asyncio.to_thread(Chats.get_chat_by_id, chat_id)
    if not chat or not chat.chat:
        return

    delete_patch = build_realtime_delete_patch(
        message_ids=[user_msg_id, asst_msg_id],
        parent_id=parent_id,
    )
    merged = merge_chat_payload(chat.chat, delete_patch)
    await asyncio.to_thread(Chats.update_chat_by_id, chat_id, merged)

    try:
        from open_webui.models.chat_messages import ChatMessages

        await asyncio.to_thread(ChatMessages.delete_message_by_id, f"{chat_id}-{user_msg_id}")
        await asyncio.to_thread(ChatMessages.delete_message_by_id, f"{chat_id}-{asst_msg_id}")
    except Exception as exc:
        log.warning("Failed to clean ChatMessages orphans: %s", exc)


from open_webui.realtime.events import emit_to_user, realtime_notification_meta  # noqa: E402 (re-export from leaf module)


def build_assistant_output_message_item(
    text: str = "", status: str = "in_progress"
) -> dict:
    return {
        "type": "message",
        "id": f"msg_{uuid4().hex}",
        "status": status,
        "role": "assistant",
        "content": [{"type": "output_text", "text": text}],
    }


def ensure_trailing_assistant_output_message(
    turn: VoiceTurn, status: str = "in_progress"
) -> dict:
    if turn.assistant_output:
        last_item = turn.assistant_output[-1]
        if last_item.get("type") == "message" and last_item.get("role") == "assistant":
            last_item["status"] = status
            content_parts = last_item.setdefault("content", [])
            if not content_parts or content_parts[-1].get("type") != "output_text":
                content_parts.append({"type": "output_text", "text": ""})
            return last_item

    message_item = build_assistant_output_message_item(status=status)
    turn.assistant_output.append(message_item)
    return message_item


async def emit_turn_output(
    session: RealtimeSession, turn: Optional[VoiceTurn], sio, done: bool = False
) -> None:
    if not turn or not turn.assistant_output:
        return

    from open_webui.utils.middleware import serialize_output

    await emit_to_user(
        sio,
        session.user_id,
        session.chat_id,
        turn.assistant_message_id,
        {
            "type": "chat:completion",
            "data": {
                "id": turn.assistant_message_id,
                "content": serialize_output(turn.assistant_output),
                "output": turn.assistant_output,
                "done": done,
                **realtime_notification_meta(session.call_id),
            },
        },
    )


async def persist_turn_output(session: RealtimeSession, turn: Optional[VoiceTurn]) -> None:
    if not turn or not turn.assistant_output:
        return

    from open_webui.utils.middleware import serialize_output

    await asyncio.to_thread(
        Chats.upsert_message_to_chat_by_id_and_message_id,
        session.chat_id,
        turn.assistant_message_id,
        {
            "id": turn.assistant_message_id,
            "role": "assistant",
            "content": serialize_output(turn.assistant_output),
            "output": turn.assistant_output,
            "model": session.model_id,
            "timestamp": int(time.time()),
        },
        advance_current=False,
    )


async def cleanup_realtime_voice_turns(
    session: RealtimeSession, sio=None, reason: str = "user"
) -> None:
    if not session.turn_state.turns or session.chat_id.startswith("local:"):
        return

    chat, messages_map = await _get_chat_history_messages(session.chat_id)
    if not chat:
        return

    for turn in list(session.turn_state.turns.values()):
        stored_user_message = messages_map.get(turn.user_message_id, {}) or {}
        stored_assistant_message = messages_map.get(turn.assistant_message_id, {}) or {}

        stored_user_content = (
            stored_user_message.get("content", "")
            if isinstance(stored_user_message.get("content", ""), str)
            else ""
        )
        stored_assistant_content = (
            stored_assistant_message.get("content", "")
            if isinstance(stored_assistant_message.get("content", ""), str)
            else ""
        )

        real_user_content = turn.user_transcript.strip()
        if not real_user_content and not _is_realtime_voice_placeholder(stored_user_content):
            real_user_content = stored_user_content.strip()

        real_assistant_content = turn.assistant_transcript.strip()
        if (
            not real_assistant_content
            and not turn.assistant_output
            and not _is_realtime_voice_placeholder(stored_assistant_content)
        ):
            real_assistant_content = stored_assistant_content.strip()

        if (
            not real_user_content
            and not real_assistant_content
            and not turn.assistant_output
        ):
            await remove_orphan_turn_messages(
                session.chat_id,
                turn.user_message_id,
                turn.assistant_message_id,
                turn.parent_message_id,
            )
            if sio:
                await emit_to_user(
                    sio,
                    session.user_id,
                    session.chat_id,
                    turn.user_message_id,
                    {"type": "chat:message:prune"},
                )
            session.turn_state.gc_turn(turn.turn_id)
            continue

        if real_user_content and stored_user_content != real_user_content:
            await asyncio.to_thread(
                Chats.upsert_message_to_chat_by_id_and_message_id,
                session.chat_id,
                turn.user_message_id,
                {
                    "id": turn.user_message_id,
                    "role": "user",
                    "content": real_user_content,
                    "timestamp": int(time.time()),
                },
                advance_current=False,
            )
            if sio:
                await emit_to_user(
                    sio,
                    session.user_id,
                    session.chat_id,
                    turn.user_message_id,
                    {
                        "type": "replace",
                        "data": {"id": turn.user_message_id, "content": real_user_content},
                    },
                )

        turn.is_assistant_done = True

        if turn.assistant_output:
            if turn.assistant_transcript:
                output_message = ensure_trailing_assistant_output_message(
                    turn, status="completed"
                )
                output_message["content"][-1]["text"] = turn.assistant_transcript
            elif (
                turn.assistant_output[-1].get("type") == "message"
                and turn.assistant_output[-1].get("role") == "assistant"
            ):
                turn.assistant_output[-1]["status"] = "completed"

            await persist_turn_output(session, turn)
            if sio:
                await emit_turn_output(session, turn, sio, done=True)
            session.turn_state.gc_turn(turn.turn_id)
            continue

        assistant_content = (
            real_assistant_content
            or stored_assistant_content
            or ASSISTANT_LISTENING_PLACEHOLDER
        )
        await asyncio.to_thread(
            Chats.upsert_message_to_chat_by_id_and_message_id,
            session.chat_id,
            turn.assistant_message_id,
            {
                "id": turn.assistant_message_id,
                "role": "assistant",
                "content": assistant_content,
                "model": session.model_id,
                "timestamp": int(time.time()),
            },
            advance_current=False,
        )
        if sio:
            await emit_to_user(
                sio,
                session.user_id,
                session.chat_id,
                turn.assistant_message_id,
                {
                    "type": "chat:completion",
                    "data": {
                        "id": turn.assistant_message_id,
                        "content": assistant_content,
                        "done": True,
                        **realtime_notification_meta(session.call_id),
                    },
                },
            )

        session.turn_state.gc_turn(turn.turn_id)


def maybe_gc_turn(session: RealtimeSession, turn: Optional[VoiceTurn]) -> None:
    if turn and turn.is_user_done and turn.is_assistant_done:
        session.turn_state.gc_turn(turn.turn_id)


def build_realtime_content_items(content) -> list[dict]:
    if isinstance(content, list):
        items = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text":
                    items.append({"type": "input_text", "text": part.get("text", "")})
                elif part.get("type") == "image_url":
                    image_url = part.get("image_url", {})
                    if isinstance(image_url, str):
                        image_url = {"url": image_url}
                    items.append(
                        {
                            "type": "input_image",
                            "image_url": image_url.get("url", ""),
                        }
                    )
        return items

    if isinstance(content, str):
        return [{"type": "input_text", "text": content}]

    visible_text = extract_visible_text_from_content(content)
    if visible_text:
        return [{"type": "input_text", "text": visible_text}]

    return []


def extract_visible_text_from_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        return "\n".join(part for part in text_parts if part).strip()
    return ""


async def get_realtime_typed_turn_metadata(request, chat_id: str) -> tuple[dict, str]:
    metadata = getattr(getattr(request, "state", None), "metadata", {}) or {}
    parent_message = metadata.get("parent_message") or {}
    assistant_message_id = str(metadata.get("message_id") or "")

    if parent_message.get("id"):
        return parent_message, assistant_message_id

    parent_message_id = str(metadata.get("parent_message_id") or "")
    if not parent_message_id or not chat_id:
        return {}, assistant_message_id

    chat = await asyncio.to_thread(Chats.get_chat_by_id, chat_id)
    if not chat or not chat.chat:
        return {}, assistant_message_id

    messages_map = chat.chat.get("history", {}).get("messages", {})
    return messages_map.get(parent_message_id) or {}, assistant_message_id


async def ensure_typed_realtime_assistant_message(
    session: RealtimeSession,
    user_message: dict,
    assistant_message_id: str,
    sio,
) -> str:
    if assistant_message_id:
        return assistant_message_id

    created_assistant_message_id = await _create_assistant_reply_message(
        session.chat_id,
        user_message.get("id", ""),
        session.model_id,
    )
    if not created_assistant_message_id:
        return ""

    if sio:
        await emit_to_user(
            sio,
            session.user_id,
            session.chat_id,
            created_assistant_message_id,
            {
                "type": "chat:message:create",
                "data": {
                    "chatId": session.chat_id,
                    "parentId": user_message.get("id"),
                    "assistantMessage": {
                        "id": created_assistant_message_id,
                        "role": "assistant",
                        "content": "",
                        "model": session.model_id,
                    },
                    "currentId": created_assistant_message_id,
                },
            },
        )

    return created_assistant_message_id


def create_realtime_text_turn(
    session: RealtimeSession,
    item_id: str,
    user_message_id: str,
    assistant_message_id: str,
    parent_message_id: str,
    user_text: str,
) -> None:
    turn_id = str(uuid4())
    session.turn_state.create_turn(
        turn_id=turn_id,
        user_message_id=user_message_id,
        assistant_message_id=assistant_message_id,
        parent_message_id=parent_message_id,
    )
    session.turn_state.bind_input_item(item_id, turn_id)
    session.turn_state.finalize_user_transcript(turn_id, user_text)


def realtime_completion_response(model_id: str = "") -> dict:
    """Return a minimal valid OpenAI Chat Completion response."""
    return {
        "id": f"rt-{uuid4().hex[:24]}",
        "object": "chat.completion",
        "model": model_id,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": ""},
                "finish_reason": "stop",
            }
        ],
    }
