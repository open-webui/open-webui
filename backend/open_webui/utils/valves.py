import base64
import hashlib
import json
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from open_webui.env import ENABLE_VALVE_ENCRYPTION, WEBUI_SECRET_KEY

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = WEBUI_SECRET_KEY.encode()
    if len(WEBUI_SECRET_KEY) != 44:
        key = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
    return Fernet(key)


def encrypt_valves(valves: dict) -> dict | str:
    if not ENABLE_VALVE_ENCRYPTION:
        return valves
    return _fernet().encrypt(json.dumps(valves).encode()).decode()


def decrypt_valves(valves) -> dict:
    if not valves:
        return {}
    if isinstance(valves, dict):
        return valves
    if not isinstance(valves, str):
        return {}

    try:
        decrypted = json.loads(_fernet().decrypt(valves.encode()).decode())
    except (InvalidToken, json.JSONDecodeError) as e:
        log.warning('Failed to decrypt valves: %s', type(e).__name__)
        return {}

    return decrypted if isinstance(decrypted, dict) else {}
