import pyotp
import qrcode
import io
import base64
from typing import List, Optional
import secrets
import hashlib
import hmac
from datetime import datetime
from loguru import logger


def generate_totp_secret() -> str:
    """Generate a secure TOTP secret key"""
    return pyotp.random_base32()


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify a TOTP code against the secret"""
    if not secret or not code:
        return False
        
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
    except Exception as e:
        logger.error(f"Error verifying TOTP code: {e}")
        return False


def generate_totp_uri(secret: str, email: str, issuer: str = "Open-WebUI") -> str:
    """Generate the TOTP URI for QR code generation"""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def generate_qr_code(uri: str) -> str:
    """Generate a QR code as a base64-encoded image"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def generate_backup_codes(count: int = 8) -> List[str]:
    """Generate backup recovery codes"""
    codes = []
    for _ in range(count):
        # Generate a 8-character code, formatted as XXXX-XXXX
        code = secrets.token_hex(4).upper()
        formatted_code = f"{code[:4]}-{code[4:]}"
        codes.append(formatted_code)
    return codes


def hash_backup_code(code: str) -> str:
    """Hash a backup code for secure storage"""
    # Remove the hyphen for hashing
    code = code.replace("-", "").upper()
    return hashlib.sha256(code.encode()).hexdigest()


def verify_backup_code(provided_code: str, hashed_codes: List[str]) -> Optional[str]:
    """Verify a backup code against a list of hashed codes
    
    Returns the matched hash if valid, or None if invalid
    """
    if not provided_code or not hashed_codes:
        return None
        
    try:
        provided_code = provided_code.replace("-", "").upper()
        hashed = hashlib.sha256(provided_code.encode()).hexdigest()
        
        # Use constant-time comparison to mitigate timing attacks
        # This prevents attackers from determining if a code is partially correct based on response times
        for stored_hash in hashed_codes:
            if hmac.compare_digest(hashed, stored_hash):
                return stored_hash
        return None
    except Exception as e:
        logger.error(f"Error verifying backup code: {e}")
        return None