import logging

from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

# Import the new encryption utility
from open_webui.utils import encryption_utils
from open_webui.utils.logger import ASSERT

# Assuming your Chat model is in a 'chats' file
from .chats import Chat
# Import Users model to fetch user-specific keys
from .users import Users # Import the Users table object to fetch user data

# Set up logging
log = logging.getLogger(__name__)

# Helper function to manage DEK context for chat operations
def _set_dek_for_chat_operation(user_id: str, db_session: Session):
    # Fetches the user's UserKey and UserEncryptedDEK from the database,
    # decrypts the UserEncryptedDEK to get the plaintext DEK, and then sets
    # this plaintext DEK in the context variable within encryption_utils.
    #
    # This DEK will then be used by encryption_utils.encrypt_message and
    # encryption_utils.decrypt_message for the current chat operation.
    #
    # Args:
    #     user_id: The ID of the user whose chat is being processed.
    #     db_session: The SQLAlchemy session to use for database queries if needed directly,
    #                 though Users.get_user_by_id typically manages its own session.
 
    if not user_id:
        ASSERT("No user_id provided for chat operation. Chat content will use mock key (if unencrypted) or fail decryption if it was user-encrypted.")
        # Explicitly set context to None, so encryption_utils.get_key() falls back to MOCK_ENCRYPTION_KEY
        encryption_utils.current_user_dek_context.set(None)
        return

    # Fetch the user. Users.get_user_by_id uses its own session via get_db().
    # If direct session usage was required: user = db_session.query(User).filter_by(id=user_id).first()
    user = Users.get_user_by_id(user_id)

    if not user:
        ASSERT(f"User not found for ID: {user_id}. Cannot set user-specific DEK. Fallback to mock key.")
        encryption_utils.current_user_dek_context.set(None)
        return

    # UserKey is temporarily stored in DB for local dev. In prod, it comes from client cert.
    # TODO: When client certs are implemented, UserKey retrieval will change.
    if not user.user_key or not user.user_encrypted_dek:
        ASSERT(f"User {user_id} is missing 'user_key' or 'user_encrypted_dek' in DB. "
                "Cannot perform user-specific encryption/decryption. Fallback to mock key.")
        encryption_utils.current_user_dek_context.set(None)
        return

    try:
        # Decrypt the UserEncryptedDEK using the UserKey to get the plaintext DEK
        dek_plaintext = encryption_utils.decrypt_dek(user.user_encrypted_dek, user.user_key)
        # Set the plaintext DEK (which is a Fernet key) in the context variable
        encryption_utils.current_user_dek_context.set(dek_plaintext)
        log.debug(f"Successfully set plaintext DEK in context for user {user_id} for chat operation.")
    except Exception as e:
        ASSERT(f"Failed to decrypt DEK for user {user_id}: {e}. Fallback to mock key.")
        encryption_utils.current_user_dek_context.set(None)

def _clear_dek_context():
    """Clears the plaintext DEK from the context variable in encryption_utils."""
    encryption_utils.current_user_dek_context.set(None)
    log.debug("Cleared DEK from context variable.")

#
# --- SQLAlchemy Event Listeners for Chat Object Encryption/Decryption ---
#
def _traverse_and_encrypt(chat_obj: Chat):
    # Helper function to traverse and encrypt message content within the chat JSON blob.
    # Uses encryption_utils.encrypt_message, which relies on the DEK set in context.
    if not isinstance(chat_obj.chat, dict) or not chat_obj.chat:
        return

    modified = False
    
    # This handles the primary message list.
    messages = chat_obj.chat.get("messages", [])
    if isinstance(messages, list):
        for message in messages:
            content = message.get("content")            # Use .get for safer access
            # Encrypt if content is a string and not already in the new encrypted format
            if isinstance(content, str) and not (isinstance(content, dict) and content.get("is_encrypted")):

                log.debug(f"ENCRYPTING content for role: {message.get('role')}")
                plaintext = content
                if not plaintext:        # Skip empty content
                    continue

                log.info(f"(CHAT MSG) BEFORE ENCRYPT: {plaintext[:30]}...")
                ciphertext = encryption_utils.encrypt_message(plaintext)
                message["content"] = {
                    "ciphertext": ciphertext,
                    "is_encrypted": True
                }

                log.info(f" CHAT MSG) AFTER ENCRYPT: {ciphertext[:30]}...")
                modified = True

    # This handles the nested history structure.
    history = chat_obj.chat.get("history", {})
    history_messages = history.get("messages", {}) if isinstance(history, dict) else {} # Ensure history itself is a dict

    if isinstance(history_messages, dict):
         for msg_id, message in history_messages.items():   # Ensure message is a dict
            content = message["content"]
            if isinstance(content, str) and not (isinstance(content, dict) and content.get("is_encrypted")):
                log.debug(f"ENCRYPTING content for role: {message.get('role')} in history (ID: {msg_id})")
                plaintext = content
                if not plaintext:
                    continue

                log.info(f"(HISTORY MSG) BEFORE ENCRYPT: {plaintext[:30]}...")
                ciphertext = encryption_utils.encrypt_message(plaintext)
                message["content"] = {
                    "ciphertext": ciphertext,
                    "is_encrypted": True
                }

                log.info(f"(HISTORY MSG) AFTER ENCRYPT: {ciphertext[:30]}...")
                modified = True

    if modified:
        # This is crucial! It tells SQLAlchemy that the JSON has changed.
        flag_modified(chat_obj, "chat")

def _traverse_and_decrypt(chat_obj: Chat):
    # Helper function to traverse and decrypt message content within the chat JSON blob.
    # Uses encryption_utils.decrypt_message, which relies on the DEK set in context.
    
    if not isinstance(chat_obj.chat, dict) or not chat_obj.chat:
        return

    # Process primary message list
    messages = chat_obj.chat.get("messages", [])
    if isinstance(messages, list):
        for message in messages:
            content_data = message.get("content")
            if isinstance(content_data, dict) and content_data.get("is_encrypted"):
                ciphertext = content_data.get('ciphertext','')
                log.info(f"(CHAT MSG) BEFORE DECRYPT: {ciphertext[:30]}...")
                try:
                    plaintext = encryption_utils.decrypt_message(ciphertext)
                    message["content"] = plaintext;
                    log.info(f"(CHAT) AFTER DECRYPT: {plaintext[:30]}...")
                except Exception as e:
                    log.error(f"DECRYPTION FAILED for chat message: {e}")
                    message["content"] = "[DECRYPTION ERROR]"       # Show error in place of content
    
    # Process nested history messages
    history = chat_obj.chat.get("history", {})
    history_messages = history.get("messages", {}) if isinstance(history, dict) else {}
    if isinstance(history_messages, dict):
        for msg_id, message in history_messages.items():
            if not isinstance(message, dict): 
                # Not expected; perhaps a malformed history entry?
                ASSERT(f"Malformed history message entry for ID {msg_id}: {message}")
                continue 
            content_data = message["content"]

            if isinstance(content_data, dict) and content_data.get("is_encrypted"):
                ciphertext = content_data.get('ciphertext','')
                log.info(f"(HISTORY MSG) BEFORE DECRYPT: {ciphertext[:30]}...")

                try:
                    plaintext = encryption_utils.decrypt_message(ciphertext)
                    message["content"] = plaintext
                    log.info(f"(HISTORY) AFTER DECRYPT: {plaintext[:30]}...")
                except Exception as e:
                    log.error(f"DECRYPTION FAILED for history message {msg_id}: {e}")
                    message["content"] = "[DECRYPTION ERROR]"

@event.listens_for(Session, 'before_flush')
def before_flush(session: Session, flush_context, instances):
    # SQLAlchemy event listener triggered before a session is flushed (i.e., before data is sent to DB).
    # It processes Chat objects that are new or modified to encrypt their content.
    log.debug("--- SQLAlchemy 'before_flush' event triggered ---")
    processed_chat_ids = set()              # To avoid double-processing if an object is in both new and dirty
    
    # Process all new Chat objects scheduled for insertion
    for obj in session.new:
        if isinstance(obj, Chat) and obj.id not in processed_chat_ids:
            log.debug(f"before_flush: Processing new Chat object ID {obj.id} for encryption.")
            try:
                _set_dek_for_chat_operation(obj.user_id, session)
                _traverse_and_encrypt(obj)  # Encrypts content in place
                processed_chat_ids.add(obj.id)
            finally:
                _clear_dek_context()        # Always clear DEK from context after operation
            
    # Process all modified Chat objects
    for obj in session.dirty:
        if isinstance(obj, Chat) and obj.id not in processed_chat_ids:
            log.debug(f"before_flush: Processing dirty Chat object ID {obj.id} for encryption.")
            try:
                # TODO: More fine-grained check? Only run if 'chat' field is actually dirty?
                # SQLAlchemy's dirty check is usually sufficient. If 'chat' wasn't changed,
                # _traverse_and_encrypt might do no work if content is already in encrypted format.
                _set_dek_for_chat_operation(obj.user_id, session)
                _traverse_and_encrypt(obj)  # Encrypts content in place
                processed_chat_ids.add(obj.id)
            finally:
                _clear_dek_context()        # Always clear DEK from context

@event.listens_for(Chat, 'load')
def after_load(target: Chat, context):
    # SQLAlchemy event listener triggered after a Chat object is loaded from the database.
    # It processes the loaded Chat object to decrypt its content.
    log.debug(f"--- SQLAlchemy 'after_load' event triggered for Chat ID: {target.id} ---")
    try:
        # Pass the session from the context if available, might be useful for _set_dek...
        db_session = context.session if hasattr(context, 'session') else None
        _set_dek_for_chat_operation(target.user_id, db_session)
        _traverse_and_decrypt(target)       # Decrypts content in place
    finally:
        _clear_dek_context()                # Always clear DEK from context
