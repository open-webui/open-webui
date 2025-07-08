import base64
import os
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# --- Mock Key for Phase 1 ---
# TODO: Remove this mock key once user-specific key derivation is fully implemented in Phase 2
# Generate a key and keep it constant for Phase 1.
# In a real scenario, this key generation part would not be here if the key was pre-defined.
# For consistent testing during development of Phase 1, print it once and then hardcode it.
# Example: MOCK_ENCRYPTION_KEY_STR = Fernet.generate_key().decode() 
# print(f"MOCK_ENCRYPTION_KEY_STR = '{MOCK_ENCRYPTION_KEY_STR}'")
MOCK_ENCRYPTION_KEY = Fernet.generate_key() # In-memory, will change on app restart. For real dev, use a hardcoded one.
# For a persistent mock key during development (replace with the output of generate_key()):
# MOCK_ENCRYPTION_KEY = b"your_generated_fernet_key_here==" 

# --- Context Variable for User DEK (Data Encryption Key) ---
# This will be used in Phase 2 to hold the per-user DEK.
# For Phase 1, encrypt_message/decrypt_message will fall back to the MOCK_ENCRYPTION_KEY if this is not set.
from contextvars import ContextVar
current_user_dek_context: ContextVar[bytes | None] = ContextVar("current_user_dek_context", default=None)

# --- Core Encryption/Decryption Functions ---

def get_key() -> bytes:
    """
    Retrieves the encryption key.
    For Phase 2: Prioritizes user-specific DEK from context variable.
    For Phase 1: Falls back to the MOCK_ENCRYPTION_KEY if no user DEK is set.
    """
    user_dek = current_user_dek_context.get()
    if user_dek:
        return user_dek
    # print("Warning: Using MOCK_ENCRYPTION_KEY. Ensure this is intended (Phase 1 or unauthenticated context).")
    return MOCK_ENCRYPTION_KEY

def encrypt_message(plaintext: str) -> str:
    """
    Encrypts a plaintext string using Fernet, then Base64 encodes the ciphertext.
    The key is retrieved via get_key().
    """
    if not plaintext:
        return plaintext # Or handle as an error, depending on requirements

    key = get_key()
    f = Fernet(key)
    try:
        token = f.encrypt(plaintext.encode('utf-8'))
        return base64.urlsafe_b64encode(token).decode('utf-8')
    except Exception as e:
        # Log error appropriately
        print(f"Encryption failed: {e}")
        raise # Or return a specific error indicator

def decrypt_message(base64_ciphertext: str) -> str:
    """
    Base64 decodes an input string, then decrypts it using Fernet.
    The key is retrieved via get_key().
    Handles potential errors during decoding or decryption.
    """
    if not base64_ciphertext:
        return base64_ciphertext # Or handle as an error

    key = get_key()
    f = Fernet(key)
    try:
        # Ensure the input is a string for decode
        if not isinstance(base64_ciphertext, str):
            # This might happen if data is already decrypted or not string type
            # print(f"Warning: decrypt_message received non-string input: {type(base64_ciphertext)}. Returning as is.")
            return str(base64_ciphertext)

        token = base64.urlsafe_b64decode(base64_ciphertext.encode('utf-8'))
        decrypted_bytes = f.decrypt(token)
        return decrypted_bytes.decode('utf-8')
    except (InvalidToken, TypeError): # TypeError for Fernet with already decrypted bytes
        # This can happen if the data is not encrypted, or encrypted with a different key,
        # or is already plaintext. Returning original data is a common strategy for idempotency.
        # print(f"Decryption failed (InvalidToken/TypeError), returning original data: {base64_ciphertext[:50]}...")
        return base64_ciphertext
    except (base64.binascii.Error, ValueError) as e: #ValueError for incorrect padding in b64decode
        # This can happen if the input is not valid Base64.
        # print(f"Base64 decoding failed, returning original data: {base64_ciphertext[:50]}...")
        return base64_ciphertext
    except Exception as e:
        # Log error appropriately
        print(f"Decryption failed with unexpected error: {e}")
        # Depending on policy, you might return original data or raise
        return base64_ciphertext # Fallback: return original data

# --- Placeholder Functions for Phase 2: User-Specific Key Management ---

def generate_salt(size: int = 16) -> bytes:
    """Generates a cryptographically secure random salt."""
    # TODO: Implement in Phase 2
    # For FIPS compliance, ensure os.urandom uses a FIPS validated CSPRNG.
    # AWS: Could use KMS GenerateRandom if direct OS access is restricted/not preferred.
    return os.urandom(size)

def derive_key_from_user_id(user_id: str, salt: bytes, iterations: int = 390000, length: int = 32) -> bytes:
    """
    Derives a key from a user_id and salt using PBKDF2-HMAC-SHA256.
    This will serve as the UserKey for encrypting the DEK.
    """
    # TODO: Implement in Phase 2
    # Iterations: OWASP recommendation is 310,000 for PBKDF2-HMAC-SHA256. NIST recommends >=10,000.
    # Check FIPS 140-2 requirements for KDFs if applicable. PBKDF2 is generally acceptable.
    # For AWS, if using KMS for key derivation, this might be different.
    # However, the spec implies UserKey is derived in-app before interacting with user_encrypted_dek.
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        iterations=iterations,
        backend=default_backend()
    )
    key = kdf.derive(user_id.encode('utf-8'))
    return key

def generate_dek() -> bytes:
    """Generates a new Data Encryption Key (DEK) using Fernet's key generation."""
    # TODO: Implement in Phase 2
    # This key will be used to encrypt/decrypt actual message content.
    # Fernet.generate_key() produces a 32-byte URL-safe base64-encoded key.
    # For AES-256-GCM, you'd need a raw 32-byte key.
    return Fernet.generate_key()

def encrypt_dek(dek: bytes, user_key: bytes) -> bytes:
    """
    Encrypts a Data Encryption Key (DEK) with a UserKey (derived from user_id).
    Uses Fernet for simplicity here.
    """
    # TODO: Implement in Phase 2
    # Ensure user_key is suitable for Fernet (it should be if it's 32 url-safe base64 bytes,
    # which PBKDF2 can output if length is 32 and then base64 encoded, or use raw bytes with AES-GCM directly)
    # For this example, assuming user_key is a Fernet-compatible key.
    # If user_key is raw bytes (e.g. from PBKDF2 direct output), you might use AES-GCM directly.
    # Let's assume user_key is a Fernet key for now for consistency with MOCK_ENCRYPTION_KEY usage.
    # If derive_key_from_user_id returns raw bytes, it needs to be base64 encoded for Fernet.
    # OR, better, use AES-GCM directly for DEK encryption if UserKey is raw.
    # For now, let's use Fernet, assuming user_key is formatted for it.
    
    # If user_key from PBKDF2 is raw 32 bytes, we need to base64 encode it to use as a Fernet key
    fernet_compatible_user_key = base64.urlsafe_b64encode(user_key)
    f = Fernet(fernet_compatible_user_key)
    encrypted_dek = f.encrypt(dek)
    return encrypted_dek # This is raw bytes, not base64 encoded again, as it's stored in BYTEA

def decrypt_dek(encrypted_dek_bytes: bytes, user_key: bytes) -> bytes:
    """
    Decrypts an encrypted Data Encryption Key (DEK) with a UserKey.
    """
    # TODO: Implement in Phase 2
    # Similar to encrypt_dek, ensure key compatibility.
    fernet_compatible_user_key = base64.urlsafe_b64encode(user_key)
    f = Fernet(fernet_compatible_user_key)
    dek = f.decrypt(encrypted_dek_bytes)
    return dek

# --- AWS KMS Specific Comments (for future reference) ---
# def encrypt_dek_kms(dek: bytes, kms_master_key_id: str, region_name: str = "your-region") -> bytes:
#     """Encrypts the DEK using AWS KMS. Returns ciphertext blob."""
#     # import boto3
#     # kms_client = boto3.client("kms", region_name=region_name)
#     # response = kms_client.encrypt(KeyId=kms_master_key_id, Plaintext=dek)
#     # return response['CiphertextBlob']

# def decrypt_dek_kms(kms_encrypted_dek: bytes, region_name: str = "your-region") -> bytes:
#     """Decrypts the DEK using AWS KMS. Returns plaintext DEK."""
#     # import boto3
#     # kms_client = boto3.client("kms", region_name=region_name)
#     # response = kms_client.decrypt(CiphertextBlob=kms_encrypted_dek)
#     # return response['Plaintext']

if __name__ == '__main__':
    # Quick test of Phase 1 functions
    print(f"Mock key being used: {MOCK_ENCRYPTION_KEY}") # For demonstration
    
    original_text = "This is a secret message!"
    
    # Simulate setting a user DEK (for testing get_key with contextvar)
    # test_user_key = Fernet.generate_key()
    # token = current_user_dek_context.set(test_user_key)
    # print(f"Using temporary context key: {test_user_key}")

    encrypted = encrypt_message(original_text)
    print(f"Original: {original_text}")
    print(f"Encrypted (Base64): {encrypted}")
    
    decrypted = decrypt_message(encrypted)
    print(f"Decrypted: {decrypted}")

    assert decrypted == original_text, "Decryption failed!"

    # Test decryption of non-encrypted data
    plain_data = "this is not encrypted"
    decrypted_plain = decrypt_message(plain_data)
    print(f"Decrypting plain data '{plain_data}': '{decrypted_plain}'")
    assert decrypted_plain == plain_data, "Decrypting plain data failed!"

    # Test decryption of invalid base64
    invalid_b64 = "this is not valid base64!@#"
    decrypted_invalid_b64 = decrypt_message(invalid_b64)
    print(f"Decrypting invalid b64 '{invalid_b64}': '{decrypted_invalid_b64}'")
    assert decrypted_invalid_b64 == invalid_b64, "Decrypting invalid b64 failed!"

    # Test placeholder functions (they are not fully implemented yet)
    print("\n--- Testing Phase 2 Placeholders (conceptual) ---")
    salt_example = generate_salt()
    print(f"Generated Salt (example): {salt_example.hex()}")

    # Note: The derive_key_from_user_id is a real implementation
    user_id_example = "user123"
    user_key_example = derive_key_from_user_id(user_id_example, salt_example)
    print(f"Derived UserKey (example, raw bytes): {user_key_example.hex()}")
    
    # Note: Fernet keys are base64 encoded. PBKDF2 output is raw bytes.
    # For Fernet, the key passed to it must be base64 URL-safe encoded.
    # So, if user_key_example is used directly with Fernet, it must be encoded first.
    # This is handled in encrypt_dek/decrypt_dek by base64 encoding the raw PBKDF2 output.

    dek_example = generate_dek() # This generates a Fernet key (base64 encoded)
    print(f"Generated DEK (example, Fernet key format): {dek_example}")

    # Encrypting the DEK (which is itself a Fernet key) using the UserKey (derived from PBKDF2)
    encrypted_dek_example = encrypt_dek(dek_example, user_key_example)
    print(f"Encrypted DEK (example, raw bytes): {encrypted_dek_example.hex()}")

    decrypted_dek_example = decrypt_dek(encrypted_dek_example, user_key_example)
    print(f"Decrypted DEK (example, Fernet key format): {decrypted_dek_example}")
    
    assert dek_example == decrypted_dek_example, "DEK encryption/decryption failed!"
    
    # current_user_dek_context.reset(token) # Reset context var if it was set

    print("\nBasic tests completed for encryption_utils.")
