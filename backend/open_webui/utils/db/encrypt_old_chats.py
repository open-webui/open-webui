"""
Encryption of Old Chats Implementation for Open WebUI

Batch-encrypts historical chat contents when a user logs in using Fernet encryption to ensure old chat content is not stored in the database as plaintext. 
"""

import asyncio
import logging
from typing import Any, Optional
from sqlalchemy.orm.attributes import flag_modified
from open_webui.internal.db import get_db_context
from open_webui.models.chats import Chat
from open_webui.utils.db.chat_encryption import encrypt_content

log = logging.getLogger(__name__)


# Encryption checks
def is_encrypted_string(s: str) -> bool:
    """Return True if string is Fernet-encrypted."""
    return isinstance(s, str) and s.startswith("gAAAAAB")


def chat_is_encrypted(chat_json: dict) -> bool:
    """Return True if all chat message contents are encrypted."""
    history = chat_json.get("history", {})
    messages = history.get("messages", {})
    for m in messages.values():
        content = m.get("content")
        if isinstance(content, str) and not is_encrypted_string(content):
            return False
    for msg in chat_json.get("messages", []):
        content = msg.get("content")
        if isinstance(content, str) and not is_encrypted_string(content):
            return False
    return True


# Old chat encryption function (encrypt all plaintext chats for a user in batches)
async def encrypt_old_chats_for_user(user_id: Any, db: Optional[Any] = None, chunk_size: int = 100) -> int:
    """Encrypt old plaintext chats for a user asynchronously."""
    log.info("Starting old-chat encryption for user %s", user_id)
    encrypted_count = 0
    try:
        def _encrypt_chats():
            count = 0
            with get_db_context() as session:
                query = session.query(Chat).filter(Chat.user_id == user_id)
                offset = 0
                # Process chats in chunks; 
                while True:
                    batch = query.offset(offset).limit(chunk_size).all()
                    if not batch:
                        break
                    modified = False
                    for chat_item in batch:
                        chat_json = chat_item.chat
                        # Only encrypt plaintext chats 
                        if chat_json and not chat_is_encrypted(chat_json):
                            chat_item.chat = encrypt_content(chat_json)
                            flag_modified(chat_item, "chat")
                            modified = True
                            count += 1
                    if modified:
                        try:
                            session.commit()
                        except Exception as e:
                            log.exception("Failed to commit encrypted chats: %s", e)
                            session.rollback()
                            raise
                    offset += chunk_size
            return count
        
        encrypted_count = await asyncio.to_thread(_encrypt_chats)
        log.info("Successfully encrypted %d chats for user %s", encrypted_count, user_id)
    except Exception as e:
        log.exception("Error encrypting old chats for user %s: %s", user_id, e)
    return encrypted_count