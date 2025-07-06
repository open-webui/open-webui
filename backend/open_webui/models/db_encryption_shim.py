from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from open_webui.models.chats import Chat

import logging
log = logging.getLogger(__name__)

def _encrypt_chat_messages(chat_obj: Chat):
    """
    Helper function to traverse and 'encrypt'/'decrypt' message content.
    FOR TESTING: It now only runs for a specific hardcoded user ID.
    """
    if not isinstance(chat_obj.chat, dict):
        log.warning(f"Chat object for ID {chat_obj.id} is not a dict")
        return

    if not chat_obj.chat:
        return

    modified = False

    # Process list-style chat["messages"]
    messages = chat_obj.chat.get("messages", [])
    for message in messages:
        if "content" in message and message["content"]:
            content = message["content"]
            if isinstance(content, str) and not (isinstance(content, dict) and content.get("is_encrypted")):
                log.info(f"_process_chat_messages (CHAT) BEFORE ENCRYPT: {content[:30]}...")
                message["content"] = {
                    "ciphertext": "12345 - " + content,
                    "is_encrypted": True
                }
                log.info(f"_process_chat_messages (CHAT) AFTER ENCRYPT: {str(message['content'])[:30]}...")
                modified = True

    # Process dict-style chat["history"]["messages"]
    history_messages = chat_obj.chat.get("history", {}).get("messages", {})
    for msg_id, message in history_messages.items():
        if "content" in message and message["content"]:
            content = message["content"]
            if isinstance(content, str) and not (isinstance(content, dict) and content.get("is_encrypted")):
                log.info(f"_process_chat_messages (HISTORY) BEFORE ENCRYPT: {content[:30]}...")
                message["content"] = {
                    "ciphertext": "12345 - " + content,
                    "is_encrypted": True
                }
                log.info(f"_process_chat_messages (HISTORY) AFTER ENCRYPT: {str(message['content'])[:30]}...")
                modified = True

    if modified:
        flag_modified(chat_obj, "chat")


# @event.listens_for(Session, "before_flush")
@event.listens_for(Chat, "before_insert")
@event.listens_for(Chat, "before_update")
def encrypt_on_save(mapper, connection, target: Chat):
    """Listen for 'before_insert' and 'before_update' events."""
    if getattr(target, "_decrypted_in_session", False):
        return

    log.debug(f"ENCRYPT_ON_SAVE event triggered for Chat ID: {target.id}")

    # # DEBUGGING: Check structure of chat field
    # assert isinstance(target.chat, dict), "Expected chat to be a dictionary"
    # history = target.chat.get("history", {})
    # assert isinstance(history, dict), "Expected chat['history'] to be a dict"
    # assert "messages" in history, "Missing 'messages' key in chat['history']"

    _encrypt_chat_messages(target)

def _decrypt_chat_messages(chat_obj: Chat):
    """
    Helper function to traverse and 'encrypt'/'decrypt' message content.
    FOR TESTING: It now only runs for a specific hardcoded user ID.
    """
    if not isinstance(chat_obj.chat, dict):
        log.warning(f"Chat object for ID {chat_obj.id} is not a dict")
        return

    if not chat_obj.chat:
        return

    modified = False

    # Process list-style chat["messages"]
    messages = chat_obj.chat.get("messages", [])
    for message in messages:
        if "content" in message and message["content"]:
            content = message["content"]
            if isinstance(content, dict) and content.get("is_encrypted"):
                log.info(f"_decrypt_chat_messages (CHAT) BEFORE DECRYPT: {str(content)[:40]}...")
                message["content"] = content["ciphertext"].replace("12345 - ", "")
                log.info(f"_decrypt_chat_messages (CHAT) AFTER DECRYPT: {str(message['content'])[:30]}...")
                modified = True

    # Process dict-style chat["history"]["messages"]
    history_messages = chat_obj.chat.get("history", {}).get("messages", {})
    for msg_id, message in history_messages.items():
        if "content" in message and message["content"]:
            content = message["content"]
            if isinstance(content, dict) and content.get("is_encrypted"):
                log.info(f"_decrypt_chat_messages (HISTORY) BEFORE DECRYPT: {str(content)[:40]}...")
                message["content"] = content["ciphertext"].replace("12345 - ", "")
                log.info(f"_decrypt_chat_messages (HISTORY) AFTER DECRYPT: {str(message['content'])[:30]}...")
                modified = True

    if modified:
        flag_modified(chat_obj, "chat")

@event.listens_for(Chat, "load")
def decrypt_on_load(target: Chat, context):
    log.debug(f"DECRYPT_ON_LOAD event triggered for Chat ID: {target.id}")
    try:
        _decrypt_chat_messages(target)
        setattr(target, "_decrypted_in_session", True)
    except Exception as e:
        print(f"[decrypt error] {e}")


class MockEncryptionService:
    def encrypt_content(self, content, key):
        print(f"encrypt_content {content}")
        return {"ciphertext": f"12345 - {content}", "is_encrypted": True}

    def decrypt_content(self, content_dict, key):
        text = content_dict.get("ciphertext", "")
        print(f"decrypt_content {text}")
        # return text.replace("12345 - ", "")
        return text

encryption_service = MockEncryptionService()
TEST_DEK = "static-test-key"