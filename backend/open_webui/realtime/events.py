"""Shared event emission helpers for the realtime package.

This is a leaf module with no internal realtime imports, allowing both
session_state.py and sideband.py to import from it without circular
dependency issues.
"""

from typing import Optional


async def emit_to_user(
    sio, user_id: str, chat_id: str, message_id: str, event_data: dict
) -> None:
    """Emit a Socket.IO event to a user's room."""
    await sio.emit(
        "events",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "data": event_data,
        },
        room=f"user:{user_id}",
    )


async def emit_status(
    sio, user_id: str, chat_id: str, call_id: str,
    description: str, done: bool
) -> None:
    """Emit a status event to the user's room."""
    await emit_to_user(
        sio,
        user_id,
        chat_id,
        "",
        {
            "type": "status",
            "data": {
                "description": description,
                "done": done,
                "callId": call_id,
            },
        },
    )


def realtime_notification_meta(call_id: Optional[str] = None) -> dict:
    """Build notification metadata for realtime events."""
    notification = {"suppress": True, "realtime": True}
    if call_id:
        notification["callId"] = call_id
    return {"notification": notification}
