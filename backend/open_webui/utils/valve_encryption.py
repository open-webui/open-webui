import base64
import hashlib
import json
import logging

from cryptography.fernet import Fernet, InvalidToken

from open_webui.env import WEBUI_SECRET_KEY

log = logging.getLogger(__name__)

_DEFAULT_SECRET = "t0p-s3cr3t"


def _make_fernet(key: str) -> Fernet:
    """Derive a Fernet instance from an arbitrary string key."""
    try:
        return Fernet(key.encode())
    except Exception:
        key_bytes = hashlib.sha256(key.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key_bytes))


if WEBUI_SECRET_KEY == _DEFAULT_SECRET:
    log.warning(
        "WEBUI_SECRET_KEY is set to the default value '%s'. "
        "Encrypted valve data is trivially decryptable. "
        "Set a strong, unique WEBUI_SECRET_KEY in production.",
        _DEFAULT_SECRET,
    )

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
            result = json.loads(decrypted)
            if not isinstance(result, dict):
                log.error(
                    "Decrypted user valves produced unexpected type %s; returning empty valves.",
                    type(result).__name__,
                )
                return {}
            return result
        except InvalidToken:
            log.error(
                "Failed to decrypt user valves: key mismatch or corrupted data. "
                "Returning empty valves."
            )
            return {}
        except json.JSONDecodeError:
            log.error(
                "Decrypted user valves but got malformed JSON. Returning empty valves."
            )
            return {}
        except Exception as e:
            log.error("Unexpected error decrypting user valves: %s: %s", type(e).__name__, e)
            return {}
    return {}
