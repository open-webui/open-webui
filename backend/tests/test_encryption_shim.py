import pytest
from datetime import datetime

# These would normally be imported from your actual app
# For now, define stubs/mocks here or import the real ones once ready
def encrypt_chat_message(message: str, user_id: str) -> str:
    return f"12345 - {message}"

def decrypt_chat_message(encrypted: str, user_id: str) -> str:
    if encrypted.startswith("12345 - "):
        return encrypted[len("12345 - "):]
    return encrypted

def mock_encrypt(plaintext: str, dek: str) -> str:
    return f"{dek}:{plaintext}"

def mock_decrypt(ciphertext: str, dek: str) -> str:
    if not ciphertext.startswith(f"{dek}:"):
        raise ValueError("Invalid decryption key or malformed ciphertext")
    return ciphertext[len(dek) + 1:]

def derive_key_from_user(user_id: str) -> str:
    return f"key-{user_id}"

# ---------- Phase 1: Hook Behavior ----------

def test_encrypt_hook_adds_marker():
    result = encrypt_chat_message("Hello world", user_id="alice")
    assert result.startswith("12345 - "), "Encryption hook should prepend marker"


def test_decrypt_hook_removes_marker():
    encrypted = "12345 - Hello world"
    result = decrypt_chat_message(encrypted, user_id="alice")
    assert result == "Hello world", "Decryption hook should remove marker"

# ---------- Phase 2: Mock DEK Encryption ----------

def test_mock_encrypt_and_decrypt():
    dek = "mock-dek"
    original = "sensitive data"
    encrypted = mock_encrypt(original, dek)
    assert encrypted != original
    decrypted = mock_decrypt(encrypted, dek)
    assert decrypted == original

def test_mock_decrypt_rejects_wrong_dek():
    enc = mock_encrypt("data", "correct-dek")
    with pytest.raises(ValueError):
        mock_decrypt(enc, "wrong-dek")

# ---------- Phase 3: Per-User Encryption ----------

def test_per_user_encryption_isolated():
    user1_key = derive_key_from_user("alice")
    user2_key = derive_key_from_user("bob")
    plaintext = "per-user secret"

    enc1 = mock_encrypt(plaintext, user1_key)
    enc2 = mock_encrypt(plaintext, user2_key)

    assert enc1 != enc2
    assert mock_decrypt(enc1, user1_key) == plaintext
    assert mock_decrypt(enc2, user2_key) == plaintext