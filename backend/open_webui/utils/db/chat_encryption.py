"""
Chat Encryption Implementation for Open WebUI

Encrypts chat content at rest using Fernet encryption to ensure chat content are not stored in the database as plaintext. 
Requires WEBUI_CHAT_ENCRYPTION_KEY environment variable to be set.
"""

import json
import logging
from cryptography.fernet import Fernet
from open_webui.env import WEBUI_CHAT_ENCRYPTION_KEY
log = logging.getLogger(__name__)

WEBUI_CHAT_ENCRYPTION_CIPHER = None


# Initialization checks
if WEBUI_CHAT_ENCRYPTION_KEY:
    try:
        WEBUI_CHAT_ENCRYPTION_CIPHER = Fernet(WEBUI_CHAT_ENCRYPTION_KEY.encode())
        log.info("Encryption Cipher initialized successfully")
    except Exception as e:
        log.error("Cipher initialization failed (Invalid Key): %s", e)
else:
    log.warning("WEBUI_CHAT_ENCRYPTION_KEY environment variable is missing: Chat encryption disabled")


# Encrypt function
def encrypt(data):
    if not WEBUI_CHAT_ENCRYPTION_CIPHER:
        return data
    if data is None:
        return None
    try:
        val = json.dumps(data) if isinstance(data, dict) else str(data)
        encrypted_data = WEBUI_CHAT_ENCRYPTION_CIPHER.encrypt(val.encode()).decode()
        return encrypted_data
    except Exception as e:
        log.error("Encryption processing failed: %s", e)
        return data


# Decrypt function
def decrypt(enc_val, plain_val):
    if not WEBUI_CHAT_ENCRYPTION_CIPHER or not enc_val or not isinstance(enc_val, str):
        return plain_val
    try:
        decrypted = WEBUI_CHAT_ENCRYPTION_CIPHER.decrypt(enc_val.encode()).decode()
        try:
            return json.loads(decrypted)
        except json.JSONDecodeError:
            return decrypted
    except Exception:
        return enc_val


def _transform_nested_text_fields(value, transform):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "text" and isinstance(item, str):
                value[key] = transform(item)
            else:
                _transform_nested_text_fields(item, transform)
    elif isinstance(value, list):
        for item in value:
            _transform_nested_text_fields(item, transform)
    return value


def _transform_content_fields(value, transform_string_content, transform_nested_text):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "content":
                if isinstance(item, str):
                    value[key] = transform_string_content(item)
                elif isinstance(item, (dict, list)):
                    value[key] = _transform_nested_text_fields(item, transform_nested_text)
            else:
                _transform_content_fields(item, transform_string_content, transform_nested_text)
    elif isinstance(value, list):
        for item in value:
            _transform_content_fields(item, transform_string_content, transform_nested_text)
    return value


# Encrypt chat content
def encrypt_content(chat_data: dict) -> dict:
    if not chat_data or not WEBUI_CHAT_ENCRYPTION_CIPHER:
        return chat_data
    
    # History
    messages_dict = chat_data.get("history", {}).get("messages", {})
    for msg_id in messages_dict:
        _transform_content_fields(messages_dict[msg_id], encrypt, encrypt)
            
        
    # Messages
    messages_list = chat_data.get("messages", [])
    for msg in messages_list:
        _transform_content_fields(msg, encrypt, encrypt)
            
    return chat_data


# Decrypt chat content
def decrypt_content(chat_data: dict) -> dict:
    if not chat_data or not WEBUI_CHAT_ENCRYPTION_CIPHER:
        return chat_data

    # History 
    messages_dict = chat_data.get("history", {}).get("messages", {})
    for msg_id in messages_dict:
        _transform_content_fields(
            messages_dict[msg_id],
            lambda s: decrypt(s, s),
            lambda s: decrypt(s, s),
        )
            
    # Messages
    messages_list = chat_data.get("messages", [])
    for msg in messages_list:
        _transform_content_fields(
            msg,
            lambda s: decrypt(s, s),
            lambda s: decrypt(s, s),
        )
            
    return chat_data


