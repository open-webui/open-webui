"""TOTP (Time-based One-Time Password) utilities for 2FA."""

from __future__ import annotations

import hashlib
import hmac
import struct
import time
import base64
import os
from typing import Tuple

TOTP_INTERVAL = 30
TOTP_DIGITS = 6
TOTP_ALGORITHM = 'sha1'


def generate_totp_secret() -> str:
    """Generate a new base32-encoded TOTP secret (20 bytes = 160 bits)."""
    return base64.b32encode(os.urandom(20)).decode('utf-8')


def _hotp(secret: bytes, counter: int, digits: int = TOTP_DIGITS) -> str:
    """HMAC-based one-time password (RFC 4226)."""
    msg = struct.pack('>Q', counter)
    h = hmac.new(secret, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = (struct.unpack('>I', h[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def _totp_value(secret_base32: str, for_time: int | None = None, interval: int = TOTP_INTERVAL) -> str:
    """Compute the current TOTP value for a given base32 secret."""
    if for_time is None:
        for_time = int(time.time())
    secret = base64.b32decode(secret_base32.upper())
    counter = for_time // interval
    return _hotp(secret, counter)


def verify_totp(secret_base32: str, code: str, window: int = 1) -> bool:
    """Verify a TOTP code with a ±window tolerance.

    Each window step is one TOTP_INTERVAL (30s), so window=1 checks
    the current, previous, and next intervals.
    """
    code = code.strip()
    if not code.isdigit() or len(code) != TOTP_DIGITS:
        return False
    now = int(time.time())
    for offset in range(-window, window + 1):
        expected = _totp_value(secret_base32, now + offset * TOTP_INTERVAL)
        if hmac.compare_digest(expected, code):
            return True
    return False


def get_totp_uri(secret_base32: str, email: str, issuer: str = 'Open WebUI') -> str:
    """Generate an otpauth:// URI for QR code display.

    Compatible with Google Authenticator, Authy, 1Password, etc.
    """
    import urllib.parse
    params = urllib.parse.urlencode({
        'secret': secret_base32,
        'issuer': issuer,
        'algorithm': TOTP_ALGORITHM.upper(),
        'digits': TOTP_DIGITS,
        'period': TOTP_INTERVAL,
    })
    label = urllib.parse.quote(f'{issuer}:{email}')
    return f'otpauth://totp/{label}?{params}'


def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate a list of single-use backup codes.

    Each code is a 12-character alphanumeric string (lowercase hex).
    """
    codes = []
    for _ in range(count):
        code = os.urandom(6).hex()  # 12 hex chars
        codes.append(code)
    return codes


def hash_backup_codes(codes: list[str]) -> list[str]:
    """Hash backup codes for secure storage.

    Uses SHA-256 so backup codes can be verified without storing plaintext.
    """
    return [hashlib.sha256(code.encode()).hexdigest() for code in codes]


def verify_backup_code(code: str, hashed_codes: list[str]) -> int | None:
    """Verify a backup code against a list of hashed codes.

    Returns the index of the matched code, or None if no match.
    The caller should remove the matched code after use.
    """
    code_hash = hashlib.sha256(code.strip().encode()).hexdigest()
    for i, stored_hash in enumerate(hashed_codes):
        if hmac.compare_digest(code_hash, stored_hash):
            return i
    return None
