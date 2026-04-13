import base64
import hashlib
import json
import logging

from cryptography.fernet import Fernet

from open_webui.env import WEBUI_SECRET_KEY

log = logging.getLogger(__name__)


def _make_fernet(key: str) -> Fernet:
    """Derive a Fernet instance from an arbitrary string key."""
    if len(key) != 44:
        key_bytes = hashlib.sha256(key.encode()).digest()
        key_encoded = base64.urlsafe_b64encode(key_bytes)
    else:
        key_encoded = key.encode()
    return Fernet(key_encoded)


_fernet = _make_fernet(WEBUI_SECRET_KEY)


def encrypt_user_valves(valves: dict) -> str:
    """Encrypt a UserValves dict to an opaque string for DB storage."""
    valves_json = json.dumps(valves)
    return _fernet.encrypt(valves_json.encode()).decode()


def decrypt_user_valves(stored) -> dict:
    """Decrypt UserValves from DB storage. Handles both encrypted (str) and legacy plaintext (dict)."""
    if isinstance(stored, dict):
        return stored
    if isinstance(stored, str):
        try:
            decrypted = _fernet.decrypt(stored.encode()).decode()
            return json.loads(decrypted)
        except Exception as e:
            log.error(f"Error decrypting user valves: {type(e).__name__}: {e}")
            raise
    return {}
