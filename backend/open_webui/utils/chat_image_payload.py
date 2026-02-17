import asyncio
import logging
from typing import Callable, Optional


def _get_message_chain(messages_map: dict, message_id: str) -> list[dict]:
    if not messages_map:
        return []

    current_message = messages_map.get(message_id)
    if not current_message:
        return []

    message_list = []
    while current_message:
        message_list.insert(0, current_message)
        parent_id = current_message.get("parentId")
        current_message = messages_map.get(parent_id) if parent_id else None

    return message_list


def _has_image_part(content: object) -> bool:
    if not isinstance(content, list):
        return False

    return any(
        isinstance(item, dict) and item.get("type") == "image_url" for item in content
    )


async def append_chat_file_images_to_user_messages(
    form_data: dict,
    messages_map: dict,
    parent_message_id: Optional[str],
    image_loader: Callable[[str], Optional[str]],
    logger: Optional[logging.Logger] = None,
) -> dict:
    if not parent_message_id:
        return form_data

    db_messages = _get_message_chain(messages_map, parent_message_id)
    if not db_messages:
        return form_data

    api_user_messages = [
        message
        for message in form_data.get("messages", [])
        if message.get("role") == "user"
    ]
    db_user_messages = [
        message for message in db_messages if message.get("role") == "user"
    ]

    for api_message, db_message in zip(api_user_messages, db_user_messages):
        content = api_message.get("content")
        if _has_image_part(content):
            continue

        image_parts = []
        for file_item in db_message.get("files") or []:
            content_type = (file_item.get("content_type") or "").lower()
            if not content_type.startswith("image/"):
                continue

            image_source = file_item.get("url") or file_item.get("id")
            if not image_source:
                continue

            try:
                image_base64 = await asyncio.to_thread(image_loader, image_source)
            except Exception as e:
                if logger:
                    logger.debug(f"Error converting chat file image to base64: {e}")
                continue

            if image_base64:
                image_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": image_base64},
                    }
                )

        if not image_parts:
            continue

        if isinstance(content, str):
            api_message["content"] = [{"type": "text", "text": content}] + image_parts
        elif isinstance(content, list):
            api_message["content"] = content + image_parts
        else:
            api_message["content"] = image_parts

    return form_data
