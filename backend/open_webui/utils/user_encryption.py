import base64
import json
import logging
import os
import secrets
from typing import Dict, Optional

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from open_webui.models.user_data_keys import UserDataKeys

log = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Custom exception for encryption/decryption errors."""

    pass


class UserEncryptionConfig:
    """Configuration for user-based encryption."""

    @classmethod
    def is_encryption_enabled(cls) -> bool:
        """Check if user encryption is enabled via environment variable."""
        return os.environ.get("ENABLE_CHAT_ENCRYPTION", "false").lower() == "true"

    @classmethod
    def log_config_status(cls) -> None:
        """Log the current encryption configuration status."""
        enabled = cls.is_encryption_enabled()
        log.info(f"User-based encryption: {'ENABLED' if enabled else 'DISABLED'}")

        if enabled:
            log.info("Encryption config - Using per-user AES-256-GCM keys")


class UserDataEncryptionService:
    """
    TEE-safe encryption service for per-user data encryption using AES-256-GCM.
    """

    def __init__(self):
        self.key_service_base_url = os.getenv("KEY_SERVICE_BASE_URL")
        if not self.key_service_base_url:
            raise Exception("KEY_SERVICE_BASE_URL is not set")

        # In-memory cache for decrypted keys to avoid repeated API calls
        self._key_cache: Dict[str, bytes] = {}

    def _generate_new_data_key(self) -> str:
        """Generate a new encrypted data key from the external key service."""
        url = f"{self.key_service_base_url}/keys"
        response = requests.post(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        if "key" not in data:
            raise Exception("Invalid response from key service")

        return data["key"]

    def _decrypt_data_key(self, encrypted_key: str) -> str:
        """Decrypt an encrypted data key using the external key service."""
        url = f"{self.key_service_base_url}/keys/decrypt"
        payload = {"key": encrypted_key}
        response = requests.post(url, json=payload, timeout=30)

        if not response.ok:
            error_text = response.text
            raise Exception(f"Key service error {response.status_code}: {error_text}")

        data = response.json()
        if "decryptedKey" not in data:
            raise Exception("Invalid response from key service")

        return data["decryptedKey"]

    def _get_user_encryption_key(self, user_id: str) -> bytes:
        """Get or create a user's encryption key as bytes for AES-256-GCM."""
        # Check cache first
        if user_id in self._key_cache:
            return self._key_cache[user_id]

        # Check if user already has a data key in database
        existing_key = UserDataKeys.get_user_data_key_by_user_id(user_id)

        if existing_key:
            # User has an existing key
            encrypted_key = existing_key.encrypted_data_key
        else:
            # User doesn't have a key, generate and store a new one
            encrypted_key = self._generate_new_data_key()

            user_data_key = UserDataKeys.create_user_data_key(
                user_id=user_id, encrypted_data_key=encrypted_key
            )

            if not user_data_key:
                raise Exception("Failed to store user data key")

        # Decrypt, validate, and cache the key
        decrypted_key_hex = self._decrypt_data_key(encrypted_key)
        key_bytes = bytes.fromhex(decrypted_key_hex)

        if len(key_bytes) != 32:
            raise Exception("Invalid key length")

        self._key_cache[user_id] = key_bytes
        return key_bytes

    def clear_cache(self, user_id: Optional[str] = None) -> None:
        """Clear cached decrypted keys."""
        if user_id:
            self._key_cache.pop(user_id, None)
        else:
            self._key_cache.clear()

    def encrypt_data(self, data: dict, user_id: str) -> str:
        """Encrypt data using AES-256-GCM with the user's encryption key."""
        if not isinstance(data, dict):
            raise EncryptionError(f"Expected dict, got {type(data)}")

        # Get user's encryption key
        key = self._get_user_encryption_key(user_id)

        # Convert dict to JSON string
        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        plaintext = json_str.encode("utf-8")

        # Create AESGCM instance and encrypt
        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Combine nonce + ciphertext and return base64 encoded
        encrypted_data = nonce + ciphertext
        return base64.b64encode(encrypted_data).decode("utf-8")

    def decrypt_data(self, encrypted_data: str, user_id: str) -> dict:
        """Decrypt data using AES-256-GCM with the user's encryption key."""
        # Handle empty data
        if not encrypted_data or not isinstance(encrypted_data, str):
            return {}

        encrypted_data = encrypted_data.strip()
        if not encrypted_data:
            return {}

        # Check if data is not encrypted (backward compatibility with plain JSON)
        if not self.is_encrypted(encrypted_data):
            try:
                return json.loads(encrypted_data)
            except json.JSONDecodeError:
                return {}

        # Decrypt AES-256-GCM data
        try:
            # Get user's encryption key
            key = self._get_user_encryption_key(user_id)

            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode("utf-8"))

            # Extract nonce and ciphertext (nonce is first 12 bytes)
            if len(encrypted_bytes) < 12:
                return {}

            nonce = encrypted_bytes[:12]
            ciphertext = encrypted_bytes[12:]

            # Decrypt and parse JSON
            aesgcm = AESGCM(key)
            decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            return json.loads(decrypted_bytes.decode("utf-8"))

        except Exception:
            # Graceful degradation: return empty dict instead of crashing
            return {}

    def is_encrypted(self, data: str) -> bool:
        """Check if data is a base64 string."""
        return self._is_base64_encoded(data)

    def _is_base64_encoded(self, data: str) -> bool:
        """Check if data is a valid base64 string."""
        if not data or not isinstance(data, str):
            return False

        try:
            base64.b64decode(data, validate=True)
            return True
        except Exception:
            return False


# Singleton pattern for global encryption instance
_user_encryption_service: Optional[UserDataEncryptionService] = None


def _get_encryption_service() -> UserDataEncryptionService:
    """Get or create global encryption service instance."""
    global _user_encryption_service
    if _user_encryption_service is None:
        try:
            _user_encryption_service = UserDataEncryptionService()
        except Exception as e:
            log.error(f"Failed to initialize global encryption service: {e}")
            raise
    return _user_encryption_service


# Convenience functions for backward compatibility and ease of use
def encrypt_chat_data(chat_data: dict, user_id: str) -> str:
    """
    Convenience function to encrypt chat data for a specific user.

    Args:
        chat_data (dict): Dictionary to encrypt
        user_id (str): User ID to encrypt for

    Returns:
        str: Base64 encoded encrypted string

    Raises:
        EncryptionError: If encryption fails
    """
    return _get_encryption_service().encrypt_data(chat_data, user_id)


def decrypt_chat_data(encrypted_data: str, user_id: str) -> dict:
    """
    Convenience function to decrypt chat data for a specific user.

    Args:
        encrypted_data (str): Base64 encoded encrypted string or plain JSON
        user_id (str): User ID to decrypt for

    Returns:
        dict: Decrypted dictionary
    """
    return _get_encryption_service().decrypt_data(encrypted_data, user_id)


def is_chat_data_encrypted(data: str) -> bool:
    """
    Convenience function to check if data is encrypted.

    Args:
        data (str): String data to check

    Returns:
        bool: True if encrypted, False otherwise
    """
    try:
        return _get_encryption_service().is_encrypted(data)
    except Exception:
        return False


def get_user_data_encryption_key(user_id: str) -> str:
    """Get a user's data encryption key in hex format (for backward compatibility)."""
    key_bytes = _get_encryption_service()._get_user_encryption_key(user_id)
    return key_bytes.hex()


def clear_encryption_cache(user_id: Optional[str] = None) -> None:
    """Clear cached encryption keys."""
    _get_encryption_service().clear_cache(user_id)


def encrypt_title_data(title: str, user_id: str) -> str:
    """
    Convenience function to encrypt title string for a specific user.

    Args:
        title (str): Title string to encrypt
        user_id (str): User ID to encrypt for

    Returns:
        str: Base64 encoded encrypted string

    Raises:
        EncryptionError: If encryption fails
    """
    if not title or not isinstance(title, str):
        return title or ""

    # Convert string to dict format for encryption
    title_data = {"title": title}
    return _get_encryption_service().encrypt_data(title_data, user_id)


def decrypt_title_data(encrypted_data: str, user_id: str) -> str:
    """
    Convenience function to decrypt title data for a specific user.

    Args:
        encrypted_data (str): Base64 encoded encrypted string or plain text
        user_id (str): User ID to decrypt for

    Returns:
        str: Decrypted title string
    """
    if not encrypted_data or not isinstance(encrypted_data, str):
        return encrypted_data or ""

    encrypted_data = encrypted_data.strip()
    if not encrypted_data:
        return ""

    try:
        # Try to decrypt the data
        decrypted_data = _get_encryption_service().decrypt_data(encrypted_data, user_id)
        return (
            decrypted_data.get("title", "") if isinstance(decrypted_data, dict) else ""
        )
    except Exception:
        # If decryption fails, return original data (it's probably not encrypted)
        return encrypted_data
