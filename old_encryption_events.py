# # backend/open_webui/models/encryption_events.py

# import logging
# from sqlalchemy import event
# from sqlalchemy.orm.attributes import flag_modified

# from open_webui.models.chats import Chat
# from open_webui.services.encryption_service import dek_context, encryption_service

# log = logging.getLogger(__name__)

# def _process_chat_messages(chat_obj: Chat, mode: str):
#     """Helper function to traverse and encrypt/decrypt message content."""
    
#     # Get the active DEK from the context variable for the current request
#     dek = dek_context.get()
#     if not dek:
#         # If no key is available (e.g., user not logged in), do nothing.
#         return

#     if not (chat_obj.chat and "messages" in chat_obj.chat):
#         return

#     modified = False
#     for message in chat_obj.chat["messages"]:
#         if "content" in message and message["content"]:
#             content = message["content"]

#             # STAGE 1 - SIMPLY ADD A FIXED PREFIX TO PROVE ENCRYPTION SHIM WORKS            
#             if mode == "encrypt" and isinstance(content, str):
#                 # If content is a plain string, "encrypt" it.
#                 message["content"] = encryption_service.encrypt_content(content, dek)
#                 modified = True

#             # STAGE 2 - SIMPLY REMOVE THE FIXED PREFIX TO PROVE DECRYPTION SHIM WORKS
#             # elif mode == "decrypt" and isinstance(content, dict) and content.get("is_encrypted"):
#                 # If content is our special dictionary, "decrypt" it.
#             #     message["content"] = encryption_service.decrypt_content(content, dek)

#             # STAGE 3 - REAL ENCRYPTION/DECRYPTION
#             # This is where you would implement the actual encryption/decryption logic.
#             # For now, we will just simulate it with the mock service.
#             # if mode == "encrypt" and isinstance(content, str):
#                 # Encrypt plaintext strings
#             #     message["content"] = encryption_service.encrypt_content(content, dek)
#             #     log.debug(f"Encrypted content for message in chat {chat_obj.id}")
#             #     modified = True

#             # elif mode == "decrypt" and isinstance(content, dict) and content.get("is_encrypted"):
#                 # Decrypt structured encryption objects
#             #     message["content"] = encryption_service.decrypt_content(content, dek)
#             #     log.debug(f"Decrypted content for message in chat {chat_obj.id}")
#                 # No need to flag as modified on load

#     # IMPORTANT: If we modified the JSON, we must tell SQLAlchemy.
#     if modified:
#         flag_modified(chat_obj, "chat")


# def encrypt_on_save(mapper, connection, target: Chat):
#     """Listen for the 'before_insert' and 'before_update' events."""
#     log.debug(f"encrypt_on_save event triggered for Chat ID: {target.id}")
#     _process_chat_messages(target, mode="encrypt")


# def decrypt_on_load(target: Chat, context):
#     """Listen for the 'load' event."""
#     log.debug(f"decrypt_on_load event triggered for Chat ID: {target.id}")
#     _process_chat_messages(target, mode="decrypt")


# def register_encryption_listeners():
#     """Attaches the event listeners to the Chat model."""
#     event.listen(Chat, 'before_insert', encrypt_on_save)
#     event.listen(Chat, 'before_update', encrypt_on_save)
#     event.listen(Chat, 'load', decrypt_on_load)
#     log.info("Encryption event listeners registered for Chat model.")

# backend/open_webui/models/encryption_events.py

import logging
from sqlalchemy import event
from sqlalchemy.orm.attributes import flag_modified

from open_webui.models.chats import Chat
from open_webui.services.encryption_service import encryption_service

log = logging.getLogger(__name__)

# --- HARDCODED FOR TESTING ---
# Replace with the actual user ID of the NEW user you created.
# You can find this by looking at the 'users' table in the db.sqlite file.
TEST_USER_ID = "your-new-user-id-goes-here" 
# This is a dummy key, since our test functions don't actually use it.
TEST_DEK = b'mock-dek-for-testing'
# -----------------------------

def _process_chat_messages(chat_obj: Chat, mode: str):
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
            if mode == "encrypt" and isinstance(content, str):
                log.info(f"_process_chat_messages (list) BEFORE ENCRYPT: {content[:30]}...")
                message["content"] = encryption_service.encrypt_content(content, TEST_DEK)
                log.info(f"_process_chat_messages (list) AFTER ENCRYPT: {message['content'].get('ciphertext','')[:30]}...")
                modified = True
            elif mode == "decrypt" and isinstance(content, dict) and content.get("is_encrypted"):
                log.info(f"_process_chat_messages (list) BEFORE DECRYPT: {content.get('ciphertext','')[:40]}...")
                message["content"] = encryption_service.decrypt_content(content, TEST_DEK)
                modified = True

    # Process dict-style chat["history"]["messages"]
    history_messages = chat_obj.chat.get("history", {}).get("messages", {})
    for msg_id, message in history_messages.items():
        if "content" in message and message["content"]:
            content = message["content"]
            if mode == "encrypt" and isinstance(content, str):
                log.info(f"_process_chat_messages (dict) BEFORE ENCRYPT: {content[:30]}...")
                message["content"] = encryption_service.encrypt_content(content, TEST_DEK)
                log.info(f"_process_chat_messages (dict) AFTER ENCRYPT: {message['content'].get('ciphertext','')[:30]}...")
                modified = True
            elif mode == "decrypt" and isinstance(content, dict) and content.get("is_encrypted"):
                log.info(f"_process_chat_messages (dict) BEFORE DECRYPT: {content.get('ciphertext','')[:40]}...")
                message["content"] = encryption_service.decrypt_content(content, TEST_DEK)
                modified = True

    if modified:
        flag_modified(chat_obj, "chat")

def encrypt_on_save(mapper, connection, target: Chat):
    """Listen for 'before_insert' and 'before_update' events."""
    log.debug(f"ENCRYPT_ON_SAVE event triggered for Chat ID: {target.id}")
    _process_chat_messages(target, mode="encrypt")
    # DEBUGGING: Check structure of chat field
    assert isinstance(target.chat, dict), "Expected chat to be a dictionary"
    history = target.chat.get("history", {})
    assert isinstance(history, dict), "Expected chat['history'] to be a dict"
    assert "messages" in history, "Missing 'messages' key in chat['history']"

def decrypt_on_load(target: Chat, context):
    """Listen for the 'load' event."""
    log.debug(f"DECRYPT_ON_LOAD event triggered for Chat ID: {target.id}")
    _process_chat_messages(target, mode="decrypt")


def register_encryption_listeners():
    """Attaches the event listeners to the Chat model."""
    event.listen(Chat, 'before_insert', encrypt_on_save)
    event.listen(Chat, 'before_update', encrypt_on_save)
    event.listen(Chat, 'load', decrypt_on_load)
    log.info("TEST (Hardcoded User) encryption event listeners registered.")
