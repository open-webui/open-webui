"""Realtime-owned helpers for negotiate-time tool spec preparation."""


from typing import Optional

from open_webui.realtime.bootstrap import convert_tools_to_realtime_format


async def resolve_realtime_tool_specs(
    request,
    *,
    user,
    model_id: str,
    model_obj: dict,
    chat_id: str,
    tool_ids: Optional[list[str]],
    tool_servers: Optional[list[dict]],
    terminal_id: Optional[str],
    features: Optional[dict],
) -> list[dict]:
    from open_webui.utils.middleware import process_chat_payload

    tool_metadata = {
        "chat_id": chat_id,
        "message_id": "",
        "user_id": user.id,
        "tool_ids": tool_ids or [],
        "tool_servers": tool_servers or [],
        "terminal_id": terminal_id,
        "features": features or {},
        "params": {"function_calling": "native"},
    }
    tool_form = {
        "model": model_id,
        "messages": [],
        "tool_ids": tool_ids or [],
        "tool_servers": tool_servers or [],
        "terminal_id": terminal_id,
        "features": features or {},
    }

    tool_form, tool_metadata, _ = await process_chat_payload(
        request, tool_form, user, tool_metadata, model_obj
    )
    if not tool_metadata.get("tools"):
        return []

    return convert_tools_to_realtime_format(tool_form.get("tools", []))
