from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
import urllib.parse

import bcrypt
from cryptography.fernet import Fernet
from open_webui.env import WEBUI_SECRET_KEY

TOTP_DIGITS = 6
TOTP_PERIOD = 30
TOTP_SECRET_BYTES = 20
BACKUP_CODE_COUNT = 10
BACKUP_CODE_LENGTH = 10
BACKUP_CODE_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'


def _get_fernet() -> Fernet:
    key_bytes = hashlib.sha256(WEBUI_SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt_totp_secret(secret: str) -> str:
    return _get_fernet().encrypt(secret.encode()).decode()


def decrypt_totp_secret(encrypted_secret: str) -> str:
    return _get_fernet().decrypt(encrypted_secret.encode()).decode()


def generate_totp_secret() -> str:
    return base64.b32encode(os.urandom(TOTP_SECRET_BYTES)).decode().rstrip('=')


def _decode_base32_secret(secret: str) -> bytes:
    normalized = secret.strip().replace(' ', '').upper()
    padding = '=' * ((8 - len(normalized) % 8) % 8)
    return base64.b32decode(normalized + padding, casefold=True)


def hotp(secret: str, counter: int, digits: int = TOTP_DIGITS) -> str:
    key = _decode_base32_secret(secret)
    counter_bytes = struct.pack('>Q', counter)
    digest = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack('>I', digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**digits)).zfill(digits)


def get_totp_step(timestamp: int | None = None, period: int = TOTP_PERIOD) -> int:
    return int((timestamp if timestamp is not None else time.time()) // period)


def verify_totp(
    secret: str,
    code: str,
    *,
    timestamp: int | None = None,
    period: int = TOTP_PERIOD,
    digits: int = TOTP_DIGITS,
    window: int = 1,
    last_used_step: int | None = None,
) -> int | None:
    normalized_code = ''.join(ch for ch in str(code) if ch.isdigit())
    if len(normalized_code) != digits:
        return None

    current_step = get_totp_step(timestamp, period)
    for step in range(current_step - window, current_step + window + 1):
        if step < 0:
            continue
        if last_used_step is not None and step <= last_used_step:
            continue
        if hmac.compare_digest(hotp(secret, step, digits), normalized_code):
            return step

    return None


def build_otpauth_uri(issuer: str, account_name: str, secret: str) -> str:
    issuer = issuer or 'Open WebUI'
    label = urllib.parse.quote(f'{issuer}:{account_name}')
    params = urllib.parse.urlencode(
        {
            'secret': secret,
            'issuer': issuer,
            'algorithm': 'SHA1',
            'digits': str(TOTP_DIGITS),
            'period': str(TOTP_PERIOD),
        }
    )
    return f'otpauth://totp/{label}?{params}'


def generate_backup_codes(count: int = BACKUP_CODE_COUNT) -> list[str]:
    codes = []
    for _ in range(count):
        raw = ''.join(secrets.choice(BACKUP_CODE_ALPHABET) for _ in range(BACKUP_CODE_LENGTH))
        codes.append(f'{raw[:5]}-{raw[5:]}'.lower())
    return codes


def normalize_backup_code(code: str) -> str:
    return ''.join(ch for ch in str(code).upper() if ch.isalnum())


def hash_backup_code(code: str) -> str:
    normalized = normalize_backup_code(code)
    return bcrypt.hashpw(normalized.encode(), bcrypt.gensalt()).decode()


def verify_backup_code(code: str, hashed_code: str) -> bool:
    normalized = normalize_backup_code(code)
    if not normalized or not hashed_code:
        return False
    return bcrypt.checkpw(normalized.encode(), hashed_code.encode())
