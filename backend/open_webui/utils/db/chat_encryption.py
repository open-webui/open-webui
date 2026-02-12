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


# Encrypt chat content
def encrypt_content(chat_data: dict) -> dict:
    if not chat_data or not WEBUI_CHAT_ENCRYPTION_CIPHER:
        return chat_data
    
    # History
    messages_dict = chat_data.get("history", {}).get("messages", {})
    for msg_id in messages_dict:
        content = messages_dict[msg_id].get("content")
        if isinstance(content, str):
            messages_dict[msg_id]["content"] = encrypt(content)
        
    # Messages
    messages_list = chat_data.get("messages", [])
    for msg in messages_list:
        content = msg.get("content")
        if isinstance(content, str):
            msg["content"] = encrypt(content)
            
    return chat_data


# Decrypt chat content
def decrypt_content(chat_data: dict) -> dict:
    if not chat_data or not WEBUI_CHAT_ENCRYPTION_CIPHER:
        return chat_data

    # History 
    messages_dict = chat_data.get("history", {}).get("messages", {})
    for msg_id in messages_dict:
        content = messages_dict[msg_id].get("content")
        if isinstance(content, str):
            messages_dict[msg_id]["content"] = decrypt(content, content)
            
    # Messages
    messages_list = chat_data.get("messages", [])
    for msg in messages_list:
        content = msg.get("content")
        if isinstance(content, str):
            msg["content"] = decrypt(content, content)
            
    return chat_data