import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from pydantic import ValidationError
from open_webui.env import ENABLE_VALVE_ENCRYPTION, WEBUI_SECRET_KEY
from open_webui.utils.json_codec import JSONCodec

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
    return _fernet().encrypt(JSONCodec.dumps(valves).encode()).decode()


def decrypt_valves(valves) -> dict:
    if not valves:
        return {}
    if isinstance(valves, dict):
        return valves
    if not isinstance(valves, str):
        return {}

    try:
        decrypted = JSONCodec.loads(_fernet().decrypt(valves.encode()).decode())
    except (InvalidToken, JSONCodec.JSONDecodeError) as e:
        log.warning('Failed to decrypt valves: %s', type(e).__name__)
        return {}

    return decrypted if isinstance(decrypted, dict) else {}


def validate_valves(module, valves):
    if hasattr(module, 'Valves'):
        values = decrypt_valves(valves) or {}
        try:
            # Validate without replacing the stored values (including unused keys/secrets).
            module.Valves(**{key: value for key, value in values.items() if value is not None})
        except Exception as error:
            detail = (
                '; '.join(
                    f'{".".join(map(str, item["loc"]))}: {item["msg"]}' for item in error.errors(include_input=False)
                )
                if isinstance(error, ValidationError)
                else str(error)
            )
            raise HTTPException(400, f'Current Valves are incompatible with this code: {detail}') from error
