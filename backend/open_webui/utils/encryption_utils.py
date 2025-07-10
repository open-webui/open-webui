import base64
import os
import hmac             # For generate_user_id
import hashlib          # For generate_user_id

from open_webui.utils.logger import ASSERT

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# --- Mock Key for Development/Fallback ---
# This key is used if a user-specific DEK is not available in the context.
# TODO: In a production AWS environment, for unauthenticated contexts or errors, decide on a strategy.
# This MOCK_ENCRYPTION_KEY should NOT be used for actual user data encryption if per-user encryption is active.
MOCK_ENCRYPTION_KEY = Fernet.generate_key() # In-memory, changes on app restart.
# For consistent development, you might hardcode a generated key:
# MOCK_ENCRYPTION_KEY = b"YfVjVgInCh_ES_pA0fFfUnKx-2YfVjVgInCh_ES_pA0=" 

# --- Local HMAC Key for User ID generation (Simulation) ---
# This key is used to simulate AWS KMS GenerateMac for UserID generation during local development.
# TODO: In AWS, replace usage of this key with actual calls to kms:GenerateMac using a dedicated KMS HMAC key.
# Ensure this is a secure, persistent key in a real local setup if needed beyond transient dev.
LOCAL_HMAC_KEY = b'12345678901234567890123456789012' # Ensure this is 32 bytes for SHA256.

# --- Context Variable for Per-User Data Encryption Key (DEK) ---
# This context variable holds the active plaintext DEK for the current user's operation.
# It's set by the db_encryption_shim before encrypt/decrypt operations and cleared afterwards.
from contextvars import ContextVar
current_user_dek_context: ContextVar[bytes | None] = ContextVar("current_user_dek_context", default=None)

# --- Core Encryption/Decryption Functions ---

def get_key() -> bytes:
    # Retrieves the encryption key for message content.
    # Prioritizes user-specific DEK from context variable if available.
    # Falls back to the MOCK_ENCRYPTION_KEY if no user DEK is set 
    # (e.g., for unauthenticated contexts, errors, or if user-specific keys are not yet implemented).
    user_dek = current_user_dek_context.get()
    if user_dek:
        # Using the per-user DEK (already in Fernet key format)
        return user_dek
    #
    # DEBUG ONLY!!!
    #
    # Fallback: Using the global mock key
    print("Warning: Using MOCK_ENCRYPTION_KEY. Ensure this is intended (Phase 1 or unauthenticated context).")    
    return MOCK_ENCRYPTION_KEY

def encrypt_message(plaintext: str) -> str:
    # Encrypts a plaintext string using Fernet, then Base64 encodes the ciphertext.
    # The key is retrieved via get_key() (which respects the user-specific DEK context).
    if not plaintext:
        return plaintext        # Or handle as an error, depending on requirements

    key = get_key()
    f = Fernet(key)
    try:
        token = f.encrypt(plaintext.encode('utf-8'))
        return base64.urlsafe_b64encode(token).decode('utf-8')
    except Exception as e:
        # Log error appropriately
        ASSERT(f"Encryption failed: {e}")
        raise                   # Or return a specific error indicator

def decrypt_message(base64_ciphertext: str) -> str:
    # Base64 decodes an input string, then decrypts it using Fernet.
    # The key is retrieved via get_key() (which respects the user-specific DEK context).
    # Handles potential errors during decoding or decryption by returning original data.
    if not base64_ciphertext:
        return base64_ciphertext        # Or handle as an error

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
    except (InvalidToken, TypeError): 
        # InvalidToken: Decryption failed (wrong key, corrupted data).
        # TypeError: Fernet might raise this if data is already decrypted bytes.
        ASSERT(f"Decryption failed: Invalid token or type error. Returning original data: {base64_ciphertext}")
        return base64_ciphertext # Return original data on decryption failure
    except (base64.binascii.Error, ValueError): 
        # Error in base64 decoding (e.g., invalid padding, non-base64 characters).
        ASSERT(f"Base64 decoding failed: {base64_ciphertext}. Returning original data.")
        return base64_ciphertext # Return original data
    except Exception as e:
        ASSERT(f"Decryption failed with unexpected error: {e}")
        return base64_ciphertext # Fallback

# --- User-Specific Key Management Functions ---

def generate_user_id(email: str, hmac_key: bytes) -> str:
    # Generates a deterministic User ID from an email address using HMAC-SHA256.
    # This simulates the AWS kms:GenerateMac operation for local development.
    # The output is a hex digest string.
    #
    # TODO: In an AWS environment, this function's logic should be replaced by a
    #       direct call to AWS KMS (kms:GenerateMac) using a dedicated KMS HMAC key.
    #
    if not isinstance(email, str):
        raise TypeError("Email must be a string.")
    if not isinstance(hmac_key, bytes):
        raise TypeError("HMAC key must be bytes.")
    return hmac.new(hmac_key, email.lower().encode('utf-8'), hashlib.sha256).hexdigest()

def generate_salt(size: int = 16) -> bytes:
    # Generates a cryptographically secure random salt.
    #
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

    # Derives a key (UserKey) from a UserID and salt using PBKDF2-HMAC-SHA256.
    # This UserKey is then used to encrypt/decrypt the user's Data Encryption Key (DEK).
    # Args:
    #     user_id: The user's unique identifier (derived from email).
    #     salt: A random salt, stored per user.
    #     iterations: Number of iterations for PBKDF2. Higher is more secure.
    #                 OWASP recommends 310,000 for PBKDF2-HMAC-SHA256 (as of early 2023).
    #                 NIST SP 800-132 recommends >=10,000.
    #     length: Desired length of the derived key in bytes (e.g., 32 for AES-256).
    # Returns:
    #     Raw bytes of the derived key.
    # TODO: Review iteration count based on performance and security requirements for production.
    #       Ensure it meets any applicable compliance standards (e.g., FIPS).
    #
    if not isinstance(user_id, str):
        raise TypeError("User ID must be a string.")
    if not isinstance(salt, bytes):
        raise TypeError("Salt must be bytes.")

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
    # Generates a new Data Encryption Key (DEK) using Fernet's key generation method.
    # This DEK is used to encrypt/decrypt the actual message content for a user.
    # It's a Fernet-compatible key (URL-safe base64 encoded, 32 bytes for AES-128-CBC).
    return Fernet.generate_key()

def encrypt_dek(dek: bytes, user_key: bytes) -> bytes:
    # Encrypts a Data Encryption Key (DEK) with a UserKey.
    # The DEK is expected to be a Fernet-compatible key (e.g., output of generate_dek()).
    # The UserKey is raw bytes (e.g., output of PBKDF2 from derive_key_from_user_id).
    # To use the raw UserKey with Fernet (which expects a base64 encoded key),
    # the UserKey is URL-safe base64 encoded before creating the Fernet object.
    # Args:
    #     dek: The plaintext DEK (Fernet key format).
    #     user_key: The raw UserKey (e.g., 32 bytes from PBKDF2).
    # Returns:
    #     Raw encrypted bytes of the DEK (suitable for storing in a BYTEA column).
    if not isinstance(dek, bytes):
        raise TypeError("DEK must be bytes.")
    if not isinstance(user_key, bytes): 
        raise TypeError("UserKey must be raw bytes.")

    fernet_compatible_user_key = base64.urlsafe_b64encode(user_key)
    f = Fernet(fernet_compatible_user_key)
    encrypted_dek = f.encrypt(dek)
    return encrypted_dek            # This is raw bytes, not base64 encoded again, as it's stored in BYTEA

def decrypt_dek(encrypted_dek_bytes: bytes, user_key: bytes) -> bytes:
    # Decrypts an encrypted Data Encryption Key (DEK) with a UserKey.
    # Args:
    #     encrypted_dek_bytes: Raw encrypted bytes of the DEK (e.g., from the database).
    #     user_key: The raw UserKey (e.g., 32 bytes from PBKDF2) used for encryption.
    # Returns:
    #     The plaintext DEK (in Fernet key format).
    if not isinstance(encrypted_dek_bytes, bytes):
        raise TypeError("Encrypted DEK must be bytes.")
    if not isinstance(user_key, bytes):
        raise TypeError("UserKey must be raw bytes.")

    fernet_compatible_user_key = base64.urlsafe_b64encode(user_key)
    f = Fernet(fernet_compatible_user_key)
    dek = f.decrypt(encrypted_dek_bytes)
    return dek

# --- AWS KMS Specific Comments (Placeholders for future AWS integration) ---
# def encrypt_dek_kms(dek: bytes, kms_master_key_id: str, region_name: str = "your-region") -> bytes:
#     # Encrypts the DEK using AWS KMS. Returns ciphertext blob.
#     # TODO: Implement with boto3 and actual KMS calls in AWS environment.
#     # import boto3
#     # kms_client = boto3.client("kms", region_name=region_name)
#     # response = kms_client.encrypt(KeyId=kms_master_key_id, Plaintext=dek)
#     # return response['CiphertextBlob']
#     pass 

# def decrypt_dek_kms(kms_encrypted_dek: bytes, region_name: str = "your-region") -> bytes:
#     # Decrypts the DEK using AWS KMS. Returns plaintext DEK.
#     # TODO: Implement with boto3 and actual KMS calls in AWS environment.
#     # import boto3
#     # kms_client = boto3.client("kms", region_name=region_name)
#     # response = kms_client.decrypt(CiphertextBlob=kms_encrypted_dek)
#     # return response['Plaintext']
#     pass


# --- Disaster Recovery Stubs (Flow 3 - Conceptual Implementation for Local Dev) ---

def stub_initiate_recovery_get_kms_dek(user_id: str) -> bytes | None:
    """
    STUB: Simulates retrieving the KmsEncryptedDEK from the user's DB record.
    In a real scenario, this would fetch `user.kms_encrypted_dek` from the database.
    TODO: Replace with actual database query when `kms_encrypted_dek` is populated.
    """
    print(f"[STUB DR] Initiating recovery for user {user_id}: Attempting to retrieve KmsEncryptedDEK.")
    # Simulate fetching: In a real app, query DB for Users.get_user_by_id(user_id).kms_encrypted_dek
    # This field is currently always None as KMS encryption isn't implemented.
    if user_id == "user_with_kms_dek_placeholder": # A dummy case for testing the flow
        # This would be actual KMS ciphertext if it were implemented.
        print("[STUB DR] Found dummy KmsEncryptedDEK for testing.")
        return b"dummy_kms_encrypted_dek_bytes_placeholder" 
    print("[STUB DR] No KmsEncryptedDEK found (as expected in current stub).")
    return None

def stub_kms_decrypt_dek(kms_encrypted_dek: bytes) -> bytes | None:
    """
    STUB: Simulates making a `kms:Decrypt` API call to the master application CMK.
    This is a highly sensitive, audited event.
    TODO: Replace with actual `boto3.client('kms').decrypt()` call in AWS.
    """
    print(f"[STUB DR] Simulating KMS Decryption for KmsEncryptedDEK: {kms_encrypted_dek[:20]}...")
    if kms_encrypted_dek == b"dummy_kms_encrypted_dek_bytes_placeholder":
        # Simulate successful KMS decryption, returning a plaintext DEK.
        # This plaintext DEK must be a Fernet key.
        recovered_dek = generate_dek() # For simplicity, generate a new one as a placeholder.
        print(f"[STUB DR] KMS Decryption successful (simulated). Plaintext DEK: {recovered_dek[:10]}...")
        return recovered_dek
    print("[STUB DR] KMS Decryption failed (simulated dummy logic).")
    return None

def stub_reprovision_user_after_kms_recovery(user_id: str, plaintext_dek: bytes) -> tuple[bytes | None, bytes | None]:
    """
    STUB: Simulates re-provisioning steps after DEK recovery via KMS.
    - Generates a new UserKey (raw random bytes, as per spec for new client cert).
    - Re-encrypts the recovered plaintext DEK with the new UserKey.
    - Logs actions that would occur in a real implementation (DB update, cert issuance).
    Returns: (new_raw_user_key, new_user_encrypted_dek) or (None, None) on failure.
    TODO: Integrate with actual User model updates and certificate issuance process.
    """
    print(f"[STUB DR] Re-provisioning user {user_id} with recovered plaintext DEK.")
    
    # 1. Generate a new random UserKey (raw 32 bytes, as spec implies for new cert).
    new_raw_user_key = os.urandom(32) 
    print(f"[STUB DR] Generated new UserKey (raw random bytes): {new_raw_user_key.hex()}")

    # 2. Re-encrypt the recovered plaintext DEK with the new UserKey
    try:
        new_user_encrypted_dek = encrypt_dek(plaintext_dek, new_raw_user_key)
        print(f"[STUB DR] Re-encrypted DEK with new UserKey: {new_user_encrypted_dek.hex()}")
        
        # 3. In a real application, these actions would follow:
        #    - Database Update:
        #      user_to_update = Users.get_user_by_id(user_id)
        #      user_to_update.user_key = new_raw_user_key # Or however it's managed for certs
        #      user_to_update.user_encrypted_dek = new_user_encrypted_dek
        #      user_to_update.salt = new_salt_if_pbkdf2_was_reused_for_new_user_key_otherwise_not_needed_if_userkey_is_random
        #      Users.update_user_by_id(user_id, {
        #          "user_key": new_raw_user_key, # Or remove if cert holds it
        #          "user_encrypted_dek": new_user_encrypted_dek,
        #          # "salt": new_salt_if_needed, # If new UserKey was PBKDF2 derived
        #      })
        #    - Certificate Issuance:
        #      A new client certificate would be issued containing the `UserID` and `new_raw_user_key`.
        print(f"[STUB DR] User {user_id} DB record would be updated with new UserEncryptedDEK (& new UserKey/Salt if applicable).")
        print(f"[STUB DR] A new client certificate for User {user_id} with the new UserKey would be issued.")
        return new_raw_user_key, new_user_encrypted_dek
    except Exception as e:
        print(f"[STUB DR] Error re-encrypting DEK for user {user_id} during reprovisioning: {e}")
        return None, None

if __name__ == '__main__':
    # This section provides basic operational tests and demonstrations of the utilities.
    # For formal unit testing, use a testing framework like pytest.

    print("--- Basic Operational Tests for encryption_utils ---")
    
    # Test User ID Generation (Simulated)
    print("\nTesting User ID Generation...")
    test_email_main = "main_user@example.com"
    # Note: LOCAL_HMAC_KEY is used here, simulating its role.
    user_id_main = generate_user_id(test_email_main, LOCAL_HMAC_KEY) 
    print(f"Generated UserID for '{test_email_main}': {user_id_main}")
    assert len(user_id_main) == 64 # SHA256 hex digest

    # Test Salt and DEK Generation
    print("\nTesting Salt & DEK Generation...")
    salt_main = generate_salt()
    dek_main_plaintext = generate_dek()
    print(f"Generated Salt (sample): {salt_main.hex()}")
    print(f"Generated DEK (Fernet key, sample): {dek_main_plaintext[:15]}...")
    assert isinstance(salt_main, bytes) and len(salt_main) == 16
    assert isinstance(dek_main_plaintext, bytes)

    # Test UserKey Derivation and DEK Encryption/Decryption
    print("\nTesting UserKey Derivation & DEK Encryption/Decryption...")
    user_key_main_raw = derive_key_from_user_id(user_id_main, salt_main) # Raw bytes from PBKDF2
    print(f"Derived UserKey (raw bytes from PBKDF2, sample): {user_key_main_raw.hex()}")
    assert len(user_key_main_raw) == 32

    encrypted_dek_main = encrypt_dek(dek_main_plaintext, user_key_main_raw)
    print(f"Encrypted DEK (raw bytes for DB, sample): {encrypted_dek_main.hex()}")
    decrypted_dek_main = decrypt_dek(encrypted_dek_main, user_key_main_raw)
    assert decrypted_dek_main == dek_main_plaintext, "DEK Encryption/Decryption cycle failed!"
    print(f"Decrypted DEK matches original: True")

    # Test Message Encryption/Decryption using the derived DEK
    print("\nTesting Message Encryption/Decryption with User-Specific DEK...")
    # Simulate setting the user's DEK in context (as db_encryption_shim would)
    token_context = current_user_dek_context.set(decrypted_dek_main) 
    
    secret_message = "This is a highly secret message for the user!"
    encrypted_message = encrypt_message(secret_message)
    print(f"Original Message: '{secret_message}'")
    print(f"Encrypted Message (Base64): '{encrypted_message}'")
    
    decrypted_message = decrypt_message(encrypted_message)
    print(f"Decrypted Message: '{decrypted_message}'")
    assert decrypted_message == secret_message, "Message E2E encryption/decryption failed with user DEK."
    
    current_user_dek_context.reset(token_context) # Clear context

    # Test Fallback to MOCK_ENCRYPTION_KEY for messages
    print("\nTesting Message Encryption/Decryption with Fallback Mock Key...")
    # Context is now clear, so get_key() should use MOCK_ENCRYPTION_KEY
    mock_key_message = "Message encrypted with mock key."
    encrypted_mock_message = encrypt_message(mock_key_message)
    decrypted_mock_message = decrypt_message(encrypted_mock_message)
    assert decrypted_mock_message == mock_key_message, "Message E2E with mock key failed."
    print(f"Mock Key Enc/Dec Cycle Passed for: '{mock_key_message}'")

    # Unit tests from previous step (for completeness of the __main__ block)
    print("\n--- Running Detailed Unit Tests (from previous step) ---")

    # Test generate_user_id
    print("\nTesting generate_user_id (detailed)...")
    _test_hmac_key_detail = os.urandom(32) 
    _uid1_detail = generate_user_id("test@example.com", _test_hmac_key_detail)
    _uid2_detail = generate_user_id("test@example.com", _test_hmac_key_detail)
    _uid3_detail = generate_user_id("test2@example.com", _test_hmac_key_detail)
    assert _uid1_detail == _uid2_detail, "generate_user_id not deterministic."
    assert _uid1_detail != _uid3_detail, "generate_user_id same for different emails."
    try:
        generate_user_id(123, _test_hmac_key_detail)
        assert False, "generate_user_id type error not raised."
    except TypeError: pass
    print("generate_user_id detailed tests passed.")

    # Test generate_salt (detailed)
    print("\nTesting generate_salt (detailed)...")
    _salt1_detail = generate_salt()
    _salt2_detail = generate_salt(32)
    assert isinstance(_salt1_detail, bytes) and len(_salt1_detail) == 16
    assert isinstance(_salt2_detail, bytes) and len(_salt2_detail) == 32
    assert _salt1_detail != generate_salt()
    print("generate_salt detailed tests passed.")

    # Test generate_dek (detailed)
    print("\nTesting generate_dek (detailed)...")
    _dek1_detail = generate_dek()
    assert isinstance(_dek1_detail, bytes)
    assert _dek1_detail != generate_dek()
    try: Fernet(_dek1_detail)
    except Exception: assert False, "generate_dek not Fernet compatible."
    print("generate_dek detailed tests passed.")

    # Test derive_key_from_user_id (detailed)
    print("\nTesting derive_key_from_user_id (detailed)...")
    _derived1_detail = derive_key_from_user_id(_uid1_detail, _salt1_detail)
    assert isinstance(_derived1_detail, bytes) and len(_derived1_detail) == 32
    print("derive_key_from_user_id detailed tests passed.")

    # Test encrypt_dek and decrypt_dek (detailed)
    print("\nTesting encrypt_dek and decrypt_dek (detailed)...")
    _user_key_detail = _derived1_detail
    _dek_to_enc_detail = generate_dek()
    _enc_dek_detail = encrypt_dek(_dek_to_enc_detail, _user_key_detail)
    assert decrypt_dek(_enc_dek_detail, _user_key_detail) == _dek_to_enc_detail
    try:
        decrypt_dek(_enc_dek_detail, os.urandom(32)) # Wrong key
        assert False, "decrypt_dek with wrong key not failed."
    except InvalidToken: pass
    print("encrypt_dek and decrypt_dek detailed tests passed.")

    # Test Disaster Recovery Stubs (Conceptual Flow)
    print("\n--- Testing Disaster Recovery Stubs (Conceptual Flow) ---")
    dr_test_user = "user_with_kms_dek_placeholder"
    dr_kms_encrypted_dek = stub_initiate_recovery_get_kms_dek(dr_test_user)
    if dr_kms_encrypted_dek:
        dr_recovered_plaintext_dek = stub_kms_decrypt_dek(dr_kms_encrypted_dek)
        if dr_recovered_plaintext_dek:
            print(f"[DR Test] Recovered Plaintext DEK (stub): {dr_recovered_plaintext_dek[:15]}...")
            dr_new_uk, dr_new_enc_dek = stub_reprovision_user_after_kms_recovery(dr_test_user, dr_recovered_plaintext_dek)
            if dr_new_uk and dr_new_enc_dek:
                print("[DR Test] Disaster recovery stub flow completed successfully.")
            else:
                print("[DR Test] Disaster recovery stub reprovisioning failed.")
        else:
            print("[DR Test] Disaster recovery stub KMS decryption failed.")
    else:
        print(f"[DR Test] Disaster recovery stub: No KmsEncryptedDEK found for user {dr_test_user} (as expected by stub).")

    print("\nAll encryption_utils tests and demonstrations completed.")
