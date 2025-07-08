import base64
import logging
# from cryptography.fernet import Fernet
from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

# Import the new encryption utility
from open_webui.utils import encryption_utils

# Assuming your Chat model is in a 'chats' file
from .chats import Chat

# Set up logging
log = logging.getLogger(__name__)

# This is a mock, hard-coded key for development.
# In a real application, this would be derived per-user from a master password.
# IMPORTANT: The key MUST be 32 bytes long and URL-safe base64 encoded.
# DEV_KEY = b'T2xMdo_2g22R1Vb-G2Yy-p-k-2gVb-G2Yy-p-k-2gVb-G2Y='
# fernet = Fernet(DEV_KEY)
# ENCRYPTED_PREFIX = "ENC:"

# def is_encrypted(content: str) -> bool:
#     """Checks if a string is already encrypted."""
#     return isinstance(content, str) and content.startswith(ENCRYPTED_PREFIX)

def _traverse_and_encrypt(chat_obj: Chat):
    """
    Helper function to traverse and encrypt message content within the chat JSON blob.
    """
    if not isinstance(chat_obj.chat, dict) or not chat_obj.chat:
        return

    modified = False
    
    # This handles the primary message list.
    messages = chat_obj.chat.get("messages", [])
    if isinstance(messages, list):
        for message in messages:
            # if "content" in message and message["content"] and not message["content"].get("is_encrypted"):
            content = message["content"]
            if isinstance(content, str) and not (isinstance(content, dict) and content.get("is_encrypted")):

                log.debug(f"ENCRYPTING content for role: {message.get('role')}")
                plaintext = message["content"]

                if not plaintext:
                    continue

                log.info(f"_traverse_and_encrypt (CHAT) BEFORE ENCRYPT: {plaintext[:30]}...")
                ciphertext = encryption_utils.encrypt_message(plaintext)
                # message["content"] = ciphertext
                message["content"] = {
                    "ciphertext": ciphertext,
                    "is_encrypted": True
                }

                if not ciphertext:
                    continue

                # encrypted_bytes = fernet.encrypt(plaintext.encode())
                #message["content"] = ENCRYPTED_PREFIX + base64.urlsafe_b64encode(encrypted_bytes).decode()
                log.info(f"_traverse_and_encrypt (CHAT) AFTER ENCRYPT: {ciphertext[:30]}...")

                modified = True

    # This handles the nested history structure.
    history_messages = chat_obj.chat.get("history", {}).get("messages", {})
    if isinstance(history_messages, dict):
         for msg_id, message in history_messages.items():
            # if "content" in message and message["content"] and not message["content"].get("is_encrypted"):
            content = message["content"]
            if isinstance(content, str) and not (isinstance(content, dict) and content.get("is_encrypted")):

                log.debug(f"ENCRYPTING content for role: {message.get('role')} in history")
                plaintext = message["content"]

                if not plaintext:
                    continue

                log.info(f"_traverse_and_encrypt (HISTORY) BEFORE ENCRYPT: {plaintext[:30]}...")
                ciphertext = encryption_utils.encrypt_message(plaintext)
                # message["content"] = cypciphertexthertext
                message["content"] = {
                    "ciphertext": ciphertext,
                    "is_encrypted": True
                }

                if not ciphertext:
                    continue

                # encrypted_bytes = fernet.encrypt(plaintext.encode())
                # message["content"] = ENCRYPTED_PREFIX + base64.urlsafe_b64encode(encrypted_bytes).decode()
                log.info(f"_traverse_and_encrypt (HISTORY) AFTER ENCRYPT: {ciphertext[:30]}...")

                modified = True

    if modified:
        # This is crucial! It tells SQLAlchemy that the JSON has changed.
        flag_modified(chat_obj, "chat")

def _traverse_and_decrypt(chat_obj: Chat):
    """
    Helper function to traverse and decrypt message content.
    """
    if not isinstance(chat_obj.chat, dict) or not chat_obj.chat:
        return

    # Process primary message list
    messages = chat_obj.chat.get("messages", [])
    if isinstance(messages, list):
        for message in messages:
            # if "content" in message and message["content"].get("is_encrypted"):
            content_data = message["content"]
            if isinstance(content_data, dict) and content_data.get("is_encrypted"):

                try:
                    #encrypted_b64 = message["content"][len(ENCRYPTED_PREFIX):]
                    #decrypted_bytes = fernet.decrypt(base64.urlsafe_b64decode(encrypted_b64))
                    #message["content"] = decrypted_bytes.decode()

                    ciphertext = message["content"].get('ciphertext','')
                    log.info(f"_traverse_and_decrypt (CHAT) BEFORE DECRYPT: {ciphertext[:40]}...")
                    # log.info(f"_decrypt_chat_messages (CHAT) BEFORE DECRYPT: {ciphertext.get('ciphertext','')[:40]}...")
                    plaintext = encryption_utils.decrypt_message(ciphertext)
                    message["content"] = plaintext;

                    log.info(f"_traverse_and_decrypt (CHAT) AFTER DECRYPT: {plaintext[:30]}...")

                except Exception as e:
                    log.error(f"DECRYPTION FAILED: {e}")
                    message["content"] = "[DECRYPTION ERROR]"
    
    # Process nested history messages
    history_messages = chat_obj.chat.get("history", {}).get("messages", {})
    if isinstance(history_messages, dict):
        for msg_id, message in history_messages.items():
            # if "content" in message and message["content"].get("is_encrypted"):
            content_data = message["content"]
            if isinstance(content_data, dict) and content_data.get("is_encrypted"):

                try:
                    # encrypted_b64 = message["content"][len(ENCRYPTED_PREFIX):]
                    # decrypted_bytes = fernet.decrypt(base64.urlsafe_b64decode(encrypted_b64))
                    # message["content"] = decrypted_bytes.decode()

                    ciphertext = message["content"].get('ciphertext','')
                    log.info(f"_traverse_and_decrypt (HISTORY) BEFORE DECRYPT: {ciphertext[:40]}...")
                    plaintext = encryption_utils.decrypt_message(ciphertext)
                    message["content"] = plaintext

                    log.info(f"_traverse_and_decrypt (HISTORY) AFTER DECRYPT: {plaintext[:30]}...")

                except Exception as e:
                    log.error(f"DECRYPTION FAILED: {e}")
                    message["content"] = "[DECRYPTION ERROR]"


@event.listens_for(Session, 'before_flush')
def before_flush(session, flush_context, instances):
    """
    Listen before the session is flushed. This is the most reliable way to
    catch all changes to the Chat object before they are written to the DB.
    """
    log.debug("--- before_flush event triggered ---")
    
    # Process all new Chat objects scheduled for insertion
    for obj in session.new:
        if isinstance(obj, Chat):
            log.debug(f"Found new Chat object, preparing to encrypt.")
            _traverse_and_encrypt(obj)
            
    # Process all modified Chat objects
    for obj in session.dirty:
        if isinstance(obj, Chat):
            log.debug(f"Found dirty Chat object: {obj.id}")
            _traverse_and_encrypt(obj)

@event.listens_for(Chat, 'load')
def after_load(target, context):
    """
    Listen for when a Chat object is loaded from the database.
    """
    log.debug(f"--- after_load event triggered for Chat ID: {target.id} ---")
    _traverse_and_decrypt(target)
