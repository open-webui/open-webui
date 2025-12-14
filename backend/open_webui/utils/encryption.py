from __future__ import annotations

from typing import Any


def is_encrypted_chat(chat_obj: Any) -> bool:
    return (
        isinstance(chat_obj, dict)
        and isinstance(chat_obj.get("enc"), dict)
        and isinstance(chat_obj.get("meta"), dict)
    )
